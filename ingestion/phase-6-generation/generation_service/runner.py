from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from generation_service.config import (
    GEN_REPAIR_ONCE,
    GEN_WRITE_LAST_JSON,
    MAX_SENTENCES,
    OUTPUT_PATH,
    PHASE43_ROOT,
    PHASE5_ROOT,
    REFUSAL_EDUCATIONAL_URL,
)
from generation_service.formatting import (
    body_without_footer,
    canonical_url,
    extract_urls,
    footer_date_from_iso,
    format_answer_three_lines,
    sentence_count,
)
from generation_service.guard import is_refusal_query
from generation_service.llm import gemini_generate

sys.path.insert(0, str(PHASE5_ROOT))
sys.path.insert(0, str(PHASE43_ROOT))
from normalize_service.metrics_extract import scheme_name_from_url_slug  # type: ignore  # noqa: E402
from retrieval_service.runner import run_retrieval  # type: ignore  # noqa: E402

logger = logging.getLogger(__name__)


def _write_generation_artifact(payload: dict[str, Any]) -> None:
    if not GEN_WRITE_LAST_JSON:
        return
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    (OUTPUT_PATH / "generation-last.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _align_answer_with_canonical_scheme(
    answer: str, grounded: list[dict[str, Any]]
) -> str:
    """
    Chroma/ Groww can store a commercial scheme_name that disagrees with the allowlist URL slug.
    Replace that stale label in the answer when we have a slug-derived canonical name.
    """
    if not answer or not grounded:
        return answer
    md = (grounded[0] or {}).get("metadata") or {}
    slug = str(md.get("slug") or "").strip()
    if not slug:
        return answer
    canonical = scheme_name_from_url_slug(slug)
    raw = str(md.get("scheme_name") or "").strip()
    if raw and raw != canonical and raw in answer:
        return answer.replace(raw, canonical)
    return answer


def _finalize_for_output(resp: GenerationResponse) -> None:
    """Set answer to 3-line layout: body | Source: url | Last updated: date."""
    grounded = (resp.retrieval or {}).get("grounded") or []
    if isinstance(grounded, list):
        resp.answer = _align_answer_with_canonical_scheme(resp.answer, grounded)
    resp.answer = format_answer_three_lines(resp.answer, resp.citation_url)
    _write_generation_artifact(resp.to_json())


@dataclass
class GenerationResponse:
    decision: str
    thread_id: str
    query: str
    answer: str
    citation_url: str | None
    validation_passed: bool
    validation_errors: list[str]
    started_at: str
    finished_at: str
    retrieval: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "thread_id": self.thread_id,
            "query": self.query,
            "answer": self.answer,
            "citation_url": self.citation_url,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "retrieval": self.retrieval,
        }


def _build_refusal(query: str) -> str:
    return "I am not authorised to answer for this question"


def _build_prompt(query: str, retrieved: list[dict[str, Any]], primary_url: str) -> str:
    chunks = []
    for i, row in enumerate(retrieved[:3], start=1):
        text = str(row.get("text") or "")
        meta = row.get("metadata") or {}
        src = str(meta.get("source_url") or "")
        fetched = str(meta.get("fetched_at") or "")
        chunks.append(f"[Chunk {i}] source_url={src} fetched_at={fetched}\n{text}")

    chunk_block = "\n\n".join(chunks)
    slug = ""
    if retrieved:
        slug = str((retrieved[0].get("metadata") or {}).get("slug") or "").strip()
    canon = (
        f"Canonical scheme name for this source page (use this exact name in your answer; "
        f"chunk text may show a different commercial or legacy name): "
        f"{scheme_name_from_url_slug(slug)}\n\n"
        if slug
        else ""
    )
    return (
        "You are a strict facts-only mutual fund assistant.\n"
        "Use only the provided chunks.\n"
        f"{canon}"
        f"Rules:\n"
        f"1) Maximum {MAX_SENTENCES} sentences.\n"
        "2) Exactly one citation URL in the body, and it must be this URL:\n"
        f"{primary_url}\n"
        "3) No advice, no comparisons, no predictions.\n"
        "4) If evidence is weak, say you couldn't find it in indexed official sources.\n\n"
        f"User question:\n{query}\n\n"
        f"Retrieved chunks:\n{chunk_block}\n\n"
        "Return only the final answer text."
    )


def _numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))


def _validate_answer(answer: str, citation_url: str, retrieved: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    body = body_without_footer(answer)
    if sentence_count(body) > MAX_SENTENCES:
        errors.append(f"sentence_count_exceeds_{MAX_SENTENCES}")

    urls = [canonical_url(u) for u in extract_urls(body)]
    expected = canonical_url(citation_url)
    if len(urls) != 1:
        errors.append("must_have_exactly_one_url")
    elif urls[0] != expected:
        errors.append("citation_url_mismatch")

    joined = " ".join(str(x.get("text") or "") for x in retrieved[:3])
    answer_nums = _numeric_tokens(body)
    source_nums = _numeric_tokens(joined)
    # Allow calendar/date tokens that may appear in natural language restatements.
    source_nums |= set(re.findall(r"\b20\d{2}\b", body))
    unsupported = sorted(n for n in answer_nums if n not in source_nums)
    if unsupported:
        errors.append(f"unsupported_numbers:{','.join(unsupported[:5])}")
    return errors


def _append_footer(answer_body: str, retrieved: list[dict[str, Any]]) -> str:
    fetched_dates = [
        str((r.get("metadata") or {}).get("fetched_at") or "")
        for r in retrieved[:3]
        if (r.get("metadata") or {}).get("fetched_at")
    ]
    date_str = footer_date_from_iso(max(fetched_dates) if fetched_dates else None)
    clean = body_without_footer(answer_body)
    return f"{clean}\n\nLast updated from sources: {date_str}"


def _extract_metric_answer(query: str, retrieved: list[dict[str, Any]], citation_url: str) -> str | None:
    if not retrieved:
        return None
    q = query.lower()
    top = retrieved[0]
    text = str(top.get("text") or "")
    md = top.get("metadata") or {}
    slug = str(md.get("slug") or "").strip()
    scheme_name = (
        scheme_name_from_url_slug(slug)
        if slug
        else str(md.get("scheme_name") or "This fund")
    )

    # Be permissive: Groww can use ₹, "Rs." / "Rs", or spacing variants.
    nav_m = re.search(
        r"NAV\s+"
        r"(?:₹|Rs\.?|INR)\s*"
        r"([0-9][0-9,]*\.?[0-9]*)\s+"
        r"per unit as of\s+"
        r"([0-9A-Za-z\.\-]+)",
        text,
        re.IGNORECASE,
    ) or re.search(
        r"NAV\s+"
        r"₹?"
        r"([0-9][0-9,]*\.?[0-9]*)\s+"
        r"per unit as of\s+"
        r"([0-9A-Za-z\.\-]+)",
        text,
        re.IGNORECASE,
    )
    sip_m = re.search(r"Minimum SIP\s+₹?([0-9][0-9,]*\.?[0-9]*)", text, re.IGNORECASE)
    aum_m = re.search(r"Fund size \(AUM\)\s+₹?([0-9][0-9,]*\.?[0-9]*)\s+Cr", text, re.IGNORECASE)
    exp_m = re.search(r"Expense ratio\s+([0-9][0-9,]*\.?[0-9]*)%\s+p\.a\.", text, re.IGNORECASE)
    rating_m = re.search(r"Groww rating\s+([0-9]+/[0-9]+)", text, re.IGNORECASE)

    wants_nav = "nav" in q or "net asset value" in q
    wants_sip = "sip" in q
    wants_aum = "aum" in q or "fund size" in q
    wants_expense = "expense ratio" in q or "ter" in q
    wants_rating = "rating" in q

    parts: list[str] = []
    if wants_nav and nav_m:
        parts.append(f"NAV for {scheme_name} is ₹{nav_m.group(1)} per unit as of {nav_m.group(2)}.")
    if wants_sip and sip_m:
        parts.append(f"Minimum SIP for {scheme_name} is ₹{sip_m.group(1)}.")
    if wants_aum and aum_m:
        parts.append(f"Fund size (AUM) for {scheme_name} is ₹{aum_m.group(1)} Cr.")
    if wants_expense and exp_m:
        parts.append(f"Expense ratio for {scheme_name} is {exp_m.group(1)}% p.a.")
    if wants_rating and rating_m:
        parts.append(f"Groww rating for {scheme_name} is {rating_m.group(1)}.")

    if not parts:
        return None
    return " ".join(parts) + f" {citation_url}"


def run_generation(query: str, thread_id: str) -> GenerationResponse:
    started = datetime.now(timezone.utc).isoformat()

    if is_refusal_query(query):
        answer = _build_refusal(query)
        finished = datetime.now(timezone.utc).isoformat()
        resp = GenerationResponse(
            decision="refuse",
            thread_id=thread_id,
            query=query,
            answer=answer,
            citation_url=None,
            validation_passed=True,
            validation_errors=[],
            started_at=started,
            finished_at=finished,
            retrieval={},
        )
        _write_generation_artifact(resp.to_json())
        return resp

    try:
        retrieval = run_retrieval(query=query, thread_id=thread_id)
        retrieval_json = retrieval.to_json()
    except Exception as exc:
        logger.exception("retrieval_failed")
        fallback_url = REFUSAL_EDUCATIONAL_URL
        answer = (
            "I am temporarily unable to retrieve indexed sources right now. "
            f"Please verify details here: {fallback_url}"
        )
        finished = datetime.now(timezone.utc).isoformat()
        resp = GenerationResponse(
            decision="temporarily_unavailable",
            thread_id=thread_id,
            query=query,
            answer=answer,
            citation_url=fallback_url,
            validation_passed=True,
            validation_errors=[],
            started_at=started,
            finished_at=finished,
            retrieval={"error": str(exc)},
        )
        _finalize_for_output(resp)
        return resp
    if retrieval.decision != "answer" or not retrieval.citation_url:
        answer = retrieval.message or "I could not find this in indexed official sources."
        answer = _append_footer(answer, retrieval_json.get("grounded") or [])
        finished = datetime.now(timezone.utc).isoformat()
        resp = GenerationResponse(
            decision="insufficient_evidence",
            thread_id=thread_id,
            query=query,
            answer=answer,
            citation_url=retrieval.citation_url,
            validation_passed=True,
            validation_errors=[],
            started_at=started,
            finished_at=finished,
            retrieval=retrieval_json,
        )
        _finalize_for_output(resp)
        return resp

    grounded = retrieval_json.get("grounded") or []
    citation_url = str(retrieval.citation_url)
    extracted = _extract_metric_answer(query=query, retrieved=grounded, citation_url=citation_url)
    if extracted:
        answer = _append_footer(extracted, grounded)
        finished = datetime.now(timezone.utc).isoformat()
        resp = GenerationResponse(
            decision="answer",
            thread_id=thread_id,
            query=query,
            answer=answer,
            citation_url=citation_url,
            validation_passed=True,
            validation_errors=[],
            started_at=started,
            finished_at=finished,
            retrieval=retrieval_json,
        )
        _finalize_for_output(resp)
        return resp

    prompt = _build_prompt(query=query, retrieved=grounded, primary_url=citation_url)
    try:
        answer_body = gemini_generate(prompt)
    except Exception as exc:
        logger.exception("generation_failed")
        answer_body = (
            "I am temporarily unable to generate a fully grounded response. "
            f"Please verify directly here: {citation_url}"
        )
        errors = [f"generation_error:{type(exc).__name__}"]
        answer = _append_footer(answer_body, grounded)
        finished = datetime.now(timezone.utc).isoformat()
        resp = GenerationResponse(
            decision="answer_fallback",
            thread_id=thread_id,
            query=query,
            answer=answer,
            citation_url=citation_url,
            validation_passed=True,
            validation_errors=errors,
            started_at=started,
            finished_at=finished,
            retrieval=retrieval_json,
        )
        _finalize_for_output(resp)
        return resp

    errors = _validate_answer(answer_body, citation_url=citation_url, retrieved=grounded)

    if errors and GEN_REPAIR_ONCE:
        joined = " ".join(str(x.get("text") or "") for x in grounded[:3])
        repair_prompt = (
            "Repair this answer so it passes all constraints.\n"
            f"Constraints failed: {errors}\n"
            f"Must include exactly one URL and it must be: {citation_url}\n"
            f"Must be <= {MAX_SENTENCES} sentences.\n"
            "No new numbers not present in source chunk.\n\n"
            f"Source chunk facts:\n{joined}\n\n"
            f"Answer to repair:\n{answer_body}"
        )
        try:
            answer_body = gemini_generate(repair_prompt)
            errors = _validate_answer(answer_body, citation_url=citation_url, retrieved=grounded)
        except Exception as exc:
            logger.exception("repair_failed")
            errors.append(f"repair_error:{type(exc).__name__}")

    if errors:
        fallback = (
            "I couldn't produce a fully validated answer from indexed official sources. "
            f"Please verify directly here: {citation_url}"
        )
        answer_body = fallback

    answer = _append_footer(answer_body, grounded)
    finished = datetime.now(timezone.utc).isoformat()
    resp = GenerationResponse(
        decision="answer" if not errors else "answer_fallback",
        thread_id=thread_id,
        query=query,
        answer=answer,
        citation_url=citation_url,
        validation_passed=(len(errors) == 0),
        validation_errors=errors,
        started_at=started,
        finished_at=finished,
        retrieval=retrieval_json,
    )
    _finalize_for_output(resp)
    return resp

