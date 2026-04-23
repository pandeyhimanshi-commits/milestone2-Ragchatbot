from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from embed_service.config import (
    DEFAULT_CHUNK_INPUT,
    DEFAULT_EMBED_OUTPUT,
    EMBEDDING_MODEL_ID,
    EMBEDDING_VERSION,
    STRICT,
)
from embed_service.encoder import embedding_dimension, encode_passages, vectors_to_jsonable

logger = logging.getLogger(__name__)


@dataclass
class EmbedJobResult:
    slug: str
    ok: bool
    error: str | None = None
    vector_count: int = 0
    output_path: str | None = None


@dataclass
class EmbedRunReport:
    started_at: str
    finished_at: str
    chunk_input: Path
    embed_output: Path
    embedding_model_id: str
    embedding_dim: int
    embedding_version: int
    results: list[EmbedJobResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "chunk_input": str(self.chunk_input),
            "embed_output": str(self.embed_output),
            "embedding_model_id": self.embedding_model_id,
            "embedding_dim": self.embedding_dim,
            "embedding_version": self.embedding_version,
            "strict": STRICT,
            "results": [
                {
                    "slug": r.slug,
                    "ok": r.ok,
                    "error": r.error,
                    "vector_count": r.vector_count,
                    "output_path": r.output_path,
                }
                for r in self.results
            ],
        }


def _discover_slugs(chunk_dir: Path) -> list[str]:
    report_path = chunk_dir / "chunk-run-report.json"
    if report_path.is_file():
        data = json.loads(report_path.read_text(encoding="utf-8"))
        slugs: list[str] = []
        for r in data.get("results", []):
            if r.get("ok") and r.get("slug") and r["slug"] != "_":
                slugs.append(str(r["slug"]))
        if slugs:
            return slugs
    slugs = []
    for p in sorted(chunk_dir.iterdir()):
        if p.is_dir() and (p / "chunks.json").is_file():
            slugs.append(p.name)
    return slugs


def embed_one(
    slug: str,
    chunk_dir: Path,
    out_dir: Path,
    dim: int,
    embedded_at: str,
) -> EmbedJobResult:
    path = chunk_dir / slug / "chunks.json"
    if not path.is_file():
        return EmbedJobResult(slug=slug, ok=False, error="missing chunks.json")

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return EmbedJobResult(slug=slug, ok=False, error=f"invalid chunks.json: {e}")

    chunks = doc.get("chunks") or []
    if not chunks:
        return EmbedJobResult(slug=slug, ok=False, error="no chunks in file")

    texts = [str(c.get("text") or "") for c in chunks]
    if not all(texts):
        return EmbedJobResult(slug=slug, ok=False, error="empty chunk text")

    try:
        mat = encode_passages(texts)
    except Exception as e:
        logger.exception("encode failed %s", slug)
        return EmbedJobResult(slug=slug, ok=False, error=str(e))

    if mat.shape[0] != len(chunks) or mat.shape[1] != dim:
        return EmbedJobResult(
            slug=slug,
            ok=False,
            error=f"embedding shape mismatch got {mat.shape} expected ({len(chunks)}, {dim})",
        )

    rows = vectors_to_jsonable(mat)
    out_chunks: list[dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        row = dict(ch)
        row["embedding"] = rows[i]
        row["embedding_model_id"] = EMBEDDING_MODEL_ID
        row["embedding_dim"] = dim
        row["embedded_at"] = embedded_at
        out_chunks.append(row)

    payload = {
        "schema_version": 1,
        "embedding_version": EMBEDDING_VERSION,
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "embedding_dim": dim,
        "slug": slug,
        "source_url": doc.get("source_url"),
        "scheme_name": doc.get("scheme_name"),
        "normalized_content_sha256": doc.get("normalized_content_sha256"),
        "doc_type": doc.get("doc_type"),
        "embedded_at": embedded_at,
        "chunks": out_chunks,
    }

    dest = out_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    out_path = dest / "embedded_chunks.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("embedded %s vectors for %s -> %s", len(out_chunks), slug, out_path)
    return EmbedJobResult(
        slug=slug,
        ok=True,
        vector_count=len(out_chunks),
        output_path=str(out_path.resolve()),
    )


def run_embed(
    chunk_input: Path | None = None,
    embed_output: Path | None = None,
) -> EmbedRunReport:
    chunk_input = chunk_input or DEFAULT_CHUNK_INPUT
    embed_output = embed_output or DEFAULT_EMBED_OUTPUT
    started = datetime.now(timezone.utc)
    embedded_at = started.isoformat()

    # Load model once to read dimension
    dim = embedding_dimension()

    report = EmbedRunReport(
        started_at=started.isoformat(),
        finished_at="",
        chunk_input=chunk_input.resolve(),
        embed_output=embed_output.resolve(),
        embedding_model_id=EMBEDDING_MODEL_ID,
        embedding_dim=dim,
        embedding_version=EMBEDDING_VERSION,
        results=[],
    )
    embed_output.mkdir(parents=True, exist_ok=True)

    slugs = _discover_slugs(chunk_input)
    if not slugs:
        report.finished_at = datetime.now(timezone.utc).isoformat()
        (embed_output / "embed-run-report.json").write_text(
            json.dumps(report.to_json(), indent=2),
            encoding="utf-8",
        )
        report.results.append(EmbedJobResult(slug="_", ok=False, error="no chunk slugs found"))
        return report

    for slug in slugs:
        report.results.append(embed_one(slug, chunk_input, embed_output, dim, embedded_at))

    report.finished_at = datetime.now(timezone.utc).isoformat()
    (embed_output / "embed-run-report.json").write_text(
        json.dumps(report.to_json(), indent=2),
        encoding="utf-8",
    )

    # Corpus manifest for downstream index (§4.6)
    manifest = {
        "generated_at": report.finished_at,
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "embedding_dim": dim,
        "embedding_version": EMBEDDING_VERSION,
        "chunk_count": sum(r.vector_count for r in report.results if r.ok),
        "slugs_ok": [r.slug for r in report.results if r.ok],
    }
    (embed_output / "corpus-manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return report


def exit_code_for_report(report: EmbedRunReport) -> int:
    if any(not r.ok for r in report.results) and STRICT:
        return 1
    if report.results and all(not r.ok for r in report.results):
        return 1
    return 0
