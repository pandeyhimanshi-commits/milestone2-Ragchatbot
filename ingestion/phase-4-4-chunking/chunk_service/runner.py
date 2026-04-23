from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chunk_service.builder import build_chunk_records
from chunk_service.config import (
    CHUNKING_VERSION,
    DEFAULT_CHUNK_OUTPUT,
    DEFAULT_METRICS_OUTPUT,
    STRICT,
)

logger = logging.getLogger(__name__)


@dataclass
class ChunkJobResult:
    slug: str
    ok: bool
    error: str | None = None
    chunk_count: int = 0
    chunks_path: str | None = None


@dataclass
class ChunkRunReport:
    started_at: str
    finished_at: str
    metrics_input: Path
    chunk_output: Path
    chunking_version: int
    results: list[ChunkJobResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metrics_input": str(self.metrics_input),
            "chunk_output": str(self.chunk_output),
            "chunking_version": self.chunking_version,
            "strict": STRICT,
            "results": [
                {
                    "slug": r.slug,
                    "ok": r.ok,
                    "error": r.error,
                    "chunk_count": r.chunk_count,
                    "chunks_path": r.chunks_path,
                }
                for r in self.results
            ],
        }


def _discover_slugs(metrics_dir: Path) -> list[str]:
    report_path = metrics_dir / "normalize-report.json"
    if report_path.is_file():
        data = json.loads(report_path.read_text(encoding="utf-8"))
        slugs: list[str] = []
        for r in data.get("results", []):
            if r.get("ok") and r.get("slug") and r["slug"] != "_":
                slugs.append(str(r["slug"]))
        if slugs:
            return slugs
    slugs = []
    for p in sorted(metrics_dir.iterdir()):
        if p.is_dir() and (p / "metrics.json").is_file():
            slugs.append(p.name)
    return slugs


def chunk_one(
    slug: str,
    metrics_dir: Path,
    out_dir: Path,
) -> ChunkJobResult:
    metrics_path = metrics_dir / slug / "metrics.json"
    if not metrics_path.is_file():
        return ChunkJobResult(slug=slug, ok=False, error="missing metrics.json")

    try:
        doc = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ChunkJobResult(slug=slug, ok=False, error=f"invalid metrics.json: {e}")

    chunks = build_chunk_records(doc)
    if not chunks:
        return ChunkJobResult(slug=slug, ok=False, error="no chunks (empty retrieval_text)")

    payload = {
        "schema_version": 1,
        "chunking_version": CHUNKING_VERSION,
        "slug": slug,
        "source_url": doc.get("source_url"),
        "scheme_name": doc.get("scheme_name"),
        "normalized_content_sha256": doc.get("normalized_content_sha256"),
        "doc_type": doc.get("doc_type"),
        "chunks": chunks,
    }

    dest = out_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    out_path = dest / "chunks.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("wrote %s chunks for %s -> %s", len(chunks), slug, out_path)
    return ChunkJobResult(
        slug=slug,
        ok=True,
        chunk_count=len(chunks),
        chunks_path=str(out_path.resolve()),
    )


def run_chunking(
    metrics_input: Path | None = None,
    chunk_output: Path | None = None,
) -> ChunkRunReport:
    metrics_input = metrics_input or DEFAULT_METRICS_OUTPUT
    chunk_output = chunk_output or DEFAULT_CHUNK_OUTPUT
    started = datetime.now(timezone.utc)
    report = ChunkRunReport(
        started_at=started.isoformat(),
        finished_at="",
        metrics_input=metrics_input.resolve(),
        chunk_output=chunk_output.resolve(),
        chunking_version=CHUNKING_VERSION,
        results=[],
    )
    chunk_output.mkdir(parents=True, exist_ok=True)

    slugs = _discover_slugs(metrics_input)
    if not slugs:
        report.finished_at = datetime.now(timezone.utc).isoformat()
        (chunk_output / "chunk-run-report.json").write_text(
            json.dumps(report.to_json(), indent=2),
            encoding="utf-8",
        )
        report.results.append(
            ChunkJobResult(slug="_", ok=False, error="no metrics slugs found")
        )
        return report

    for slug in slugs:
        report.results.append(chunk_one(slug, metrics_input, chunk_output))

    report.finished_at = datetime.now(timezone.utc).isoformat()
    (chunk_output / "chunk-run-report.json").write_text(
        json.dumps(report.to_json(), indent=2),
        encoding="utf-8",
    )
    return report


def exit_code_for_report(report: ChunkRunReport) -> int:
    if any(not r.ok for r in report.results) and STRICT:
        return 1
    if report.results and all(not r.ok for r in report.results):
        return 1
    return 0
