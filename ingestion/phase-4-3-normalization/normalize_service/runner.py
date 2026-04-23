from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from normalize_service.config import (
    DEFAULT_NORMALIZE_OUTPUT,
    DEFAULT_SCRAPE_OUTPUT,
    DOC_TYPE,
    NORMALIZE_VERSION,
    SCHEMA_VERSION,
    STRICT,
)
from normalize_service.metrics_extract import (
    build_retrieval_text,
    extract_metrics,
    scheme_name_from_url_slug,
)

logger = logging.getLogger(__name__)


@dataclass
class NormalizeResult:
    slug: str
    ok: bool
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    metrics_path: str | None = None


@dataclass
class NormalizeRunReport:
    started_at: str
    finished_at: str
    scrape_output: Path
    normalize_output: Path
    normalize_version: int
    results: list[NormalizeResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "scrape_output": str(self.scrape_output),
            "normalize_output": str(self.normalize_output),
            "schema_version": SCHEMA_VERSION,
            "normalize_version": self.normalize_version,
            "strict": STRICT,
            "results": [
                {
                    "slug": r.slug,
                    "ok": r.ok,
                    "error": r.error,
                    "warnings": r.warnings,
                    "metrics_path": r.metrics_path,
                }
                for r in self.results
            ],
        }


def _load_scrape_slugs(scrape_dir: Path) -> list[str]:
    report_path = scrape_dir / "run-report.json"
    if report_path.is_file():
        data = json.loads(report_path.read_text(encoding="utf-8"))
        slugs: list[str] = []
        for r in data.get("results", []):
            if r.get("ok") and r.get("slug"):
                slugs.append(str(r["slug"]))
        if slugs:
            return slugs
    slugs = []
    for p in sorted(scrape_dir.iterdir()):
        if p.is_dir() and (p / "body.html").is_file() and (p / "meta.json").is_file():
            slugs.append(p.name)
    return slugs


def _metrics_complete(m: dict[str, Any]) -> bool:
    metrics = m.get("metrics") or {}
    nav = (metrics.get("nav") or {}).get("value")
    sip = (metrics.get("minimum_sip") or {}).get("value")
    aum = (metrics.get("fund_size") or {}).get("value")
    ter = (metrics.get("expense_ratio") or {}).get("value")
    return all(x is not None for x in (nav, sip, aum, ter))


def normalize_one(
    slug: str,
    scrape_dir: Path,
    out_dir: Path,
) -> NormalizeResult:
    page_dir = scrape_dir / slug
    body_path = page_dir / "body.html"
    meta_path = page_dir / "meta.json"
    if not body_path.is_file() or not meta_path.is_file():
        return NormalizeResult(slug=slug, ok=False, error="missing body.html or meta.json")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    html = body_path.read_bytes()

    try:
        extracted, parse_warnings = extract_metrics(html)
    except Exception as e:
        logger.exception("metrics extract failed %s", slug)
        return NormalizeResult(slug=slug, ok=False, error=str(e))

    if extracted is None:
        return NormalizeResult(
            slug=slug,
            ok=False,
            error="; ".join(parse_warnings) if parse_warnings else "extract failed",
            warnings=parse_warnings,
        )

    metrics = extracted["metrics"]
    warnings = list(parse_warnings)
    # Align displayed scheme name with the allowlist URL slug. Groww's mfServerSideData.scheme_name
    # can disagree with the path (e.g. legacy slug still says "equity" while payload says "Flexi Cap").
    scheme_name = scheme_name_from_url_slug(slug)

    if not _metrics_complete(extracted):
        msg = "incomplete core metrics (nav, minimum_sip, fund_size, expense_ratio)"
        if STRICT:
            return NormalizeResult(
                slug=slug,
                ok=False,
                error=msg,
                warnings=warnings,
            )
        warnings.append(msg)

    normalized_at = datetime.now(timezone.utc).isoformat()
    retrieval_text = build_retrieval_text(scheme_name, metrics)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "normalize_version": NORMALIZE_VERSION,
        "doc_type": DOC_TYPE,
        "source_url": meta.get("url"),
        "fetched_at": meta.get("fetched_at"),
        "html_content_sha256": meta.get("content_sha256"),
        "http_status": meta.get("status_code"),
        "normalized_at": normalized_at,
        "scheme_name": scheme_name,
        "metrics": metrics,
        "retrieval_text": retrieval_text,
    }
    canonical = json.dumps(
        {"metrics": metrics, "source_url": payload["source_url"], "scheme_name": scheme_name},
        ensure_ascii=False,
        sort_keys=True,
    )
    payload["normalized_content_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    dest = out_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    for stale in ("normalized.json", "normalized.txt"):
        sp = dest / stale
        if sp.is_file():
            sp.unlink()
    json_path = dest / "metrics.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("wrote metrics for %s -> %s", slug, json_path)
    return NormalizeResult(
        slug=slug,
        ok=True,
        warnings=warnings,
        metrics_path=str(json_path.resolve()),
    )


def run_normalize(
    scrape_output: Path | None = None,
    normalize_output: Path | None = None,
) -> NormalizeRunReport:
    scrape_output = scrape_output or DEFAULT_SCRAPE_OUTPUT
    normalize_output = normalize_output or DEFAULT_NORMALIZE_OUTPUT
    started = datetime.now(timezone.utc)
    report = NormalizeRunReport(
        started_at=started.isoformat(),
        finished_at="",
        scrape_output=scrape_output.resolve(),
        normalize_output=normalize_output.resolve(),
        normalize_version=NORMALIZE_VERSION,
        results=[],
    )
    normalize_output.mkdir(parents=True, exist_ok=True)

    slugs = _load_scrape_slugs(scrape_output)
    if not slugs:
        report.finished_at = datetime.now(timezone.utc).isoformat()
        (normalize_output / "normalize-report.json").write_text(
            json.dumps(report.to_json(), indent=2),
            encoding="utf-8",
        )
        report.results.append(
            NormalizeResult(slug="_", ok=False, error="no scrape pages found")
        )
        return report

    for slug in slugs:
        res = normalize_one(slug, scrape_output, normalize_output)
        report.results.append(res)
        if res.ok:
            if res.warnings:
                for w in res.warnings:
                    logger.warning("%s: %s", slug, w)
        else:
            logger.error("normalize failed %s: %s", slug, res.error)

    report.finished_at = datetime.now(timezone.utc).isoformat()
    (normalize_output / "normalize-report.json").write_text(
        json.dumps(report.to_json(), indent=2),
        encoding="utf-8",
    )
    return report


def exit_code_for_report(report: NormalizeRunReport) -> int:
    if any(not r.ok for r in report.results) and STRICT:
        return 1
    if report.results and all(not r.ok for r in report.results):
        return 1
    return 0
