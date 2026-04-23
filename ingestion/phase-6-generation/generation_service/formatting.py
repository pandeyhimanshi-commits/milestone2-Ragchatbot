from __future__ import annotations

import re
from datetime import datetime

URL_RE = re.compile(r"https?://[^\s)]+")


def sentence_count(text: str) -> int:
    # Simple sentence split suitable for guardrail checks.
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    return len(parts)


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def canonical_url(url: str) -> str:
    return (url or "").strip().rstrip(".,);]\"'")


def body_without_footer(text: str) -> str:
    marker = "\n\nLast updated from sources:"
    if marker in text:
        return text.split(marker, 1)[0].strip()
    return text.strip()


def footer_date_from_iso(iso_ts: str | None) -> str:
    if not iso_ts:
        return "unknown"
    try:
        d = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return d.date().isoformat()
    except Exception:
        return "unknown"


def format_answer_three_lines(full_answer: str, citation_url: str | None) -> str:
    """
    UI layout: line 1 = answer text (no URLs), line 2 = Source: URL, line 3 = Last updated date.
    Accepts answers that include a trailing 'Last updated from sources:' block from _append_footer.
    """
    marker = "\n\nLast updated from sources:"
    if marker in (full_answer or ""):
        pre, post = (full_answer or "").split(marker, 1)
        date_value = (post or "").strip().split("\n")[0].strip() or "—"
    else:
        pre = (full_answer or "").strip()
        date_value = "—"

    body = (pre or "").strip()
    urls_in_body = extract_urls(body)
    line1 = body
    for u in urls_in_body:
        line1 = line1.replace(u, " ")
    line1 = re.sub(r"\s+", " ", line1).strip(" ,.;")
    if not line1:
        line1 = "—"

    source = (citation_url or (urls_in_body[0] if urls_in_body else "")).strip()
    if not source:
        source = "—"

    return f"{line1}\nSource: {source}\nLast updated: {date_value}"

