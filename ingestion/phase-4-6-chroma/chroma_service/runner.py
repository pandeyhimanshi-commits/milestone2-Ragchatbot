from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Load .env and default flags before chromadb initializes Settings (telemetry, etc.).
from chroma_service.config import (
    CHROMA_API_KEY,
    CHROMA_CLOUD_DATABASE,
    CHROMA_CLOUD_TENANT,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    CHROMA_USE_PERSISTENT,
    COLLECTION_NAME,
    DEFAULT_EMBED_OUTPUT,
    DEFAULT_PERSIST_DIR,
    DEFAULT_REPORT_OUTPUT,
    EMBEDDING_DIM,
    RECREATE_COLLECTION,
    STRICT,
)

import chromadb

from chroma_service.metadata import chroma_metadata

logger = logging.getLogger(__name__)


@dataclass
class ChromaIngestResult:
    slug: str
    ok: bool
    error: str | None = None
    rows: int = 0


@dataclass
class ChromaRunReport:
    started_at: str
    finished_at: str
    embed_input: Path
    deployment: str
    persist_directory: str | None
    http_host: str | None
    cloud_tenant: str | None
    cloud_database: str | None
    collection_name: str
    embedding_dim: int
    corpus_version: str
    chroma_upserted: int
    # §4.7-style ops metrics (chunking-embedding-architecture.md)
    slugs_total: int = 0
    slugs_succeeded: int = 0
    slugs_failed: int = 0
    chunks_total: int = 0
    chunk_row_errors: int = 0
    chroma_upsert_duration_ms: float | None = None
    embed_corpus_manifest: dict[str, Any] | None = None
    results: list[ChromaIngestResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "embed_input": str(self.embed_input),
            "deployment": self.deployment,
            "persist_directory": self.persist_directory,
            "http_host": self.http_host,
            "cloud_tenant": self.cloud_tenant,
            "cloud_database": self.cloud_database,
            "collection_name": self.collection_name,
            "embedding_dim": self.embedding_dim,
            "corpus_version": self.corpus_version,
            "chroma_upserted": self.chroma_upserted,
            "slugs_total": self.slugs_total,
            "slugs_succeeded": self.slugs_succeeded,
            "slugs_failed": self.slugs_failed,
            "chunks_total": self.chunks_total,
            "chunk_row_errors": self.chunk_row_errors,
            "chroma_upsert_duration_ms": self.chroma_upsert_duration_ms,
            "embed_corpus_manifest": self.embed_corpus_manifest,
            "strict": STRICT,
            "results": [
                {
                    "slug": r.slug,
                    "ok": r.ok,
                    "error": r.error,
                    "rows": r.rows,
                }
                for r in self.results
            ],
        }


def _make_client() -> tuple[
    chromadb.ClientAPI, str, str | None, str | None, str | None, str | None
]:
    """
    Returns (client, deployment, persist_dir, http_host, cloud_tenant, cloud_database).
    persist_dir is set only for persistent mode; http_host is host:port for HttpClient.
    """
    if not CHROMA_USE_PERSISTENT and CHROMA_CLOUD_TENANT and CHROMA_CLOUD_DATABASE:
        api_key = CHROMA_API_KEY or None
        logger.info(
            "Chroma CloudClient tenant=%s database=%s (api.trychroma.com)",
            CHROMA_CLOUD_TENANT,
            CHROMA_CLOUD_DATABASE,
        )
        client = chromadb.CloudClient(
            tenant=CHROMA_CLOUD_TENANT,
            database=CHROMA_CLOUD_DATABASE,
            api_key=api_key,
        )
        return client, "cloud", None, None, CHROMA_CLOUD_TENANT, CHROMA_CLOUD_DATABASE
    if not CHROMA_USE_PERSISTENT and CHROMA_HTTP_HOST:
        logger.info("Chroma HttpClient %s:%s", CHROMA_HTTP_HOST, CHROMA_HTTP_PORT)
        return (
            chromadb.HttpClient(host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT),
            "http",
            None,
            f"{CHROMA_HTTP_HOST}:{CHROMA_HTTP_PORT}",
            None,
            None,
        )
    DEFAULT_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Chroma PersistentClient %s", DEFAULT_PERSIST_DIR)
    return (
        chromadb.PersistentClient(path=str(DEFAULT_PERSIST_DIR)),
        "persistent",
        str(DEFAULT_PERSIST_DIR.resolve()),
        None,
        None,
        None,
    )


def _discover_slugs(embed_dir: Path) -> list[str]:
    report_path = embed_dir / "embed-run-report.json"
    if report_path.is_file():
        data = json.loads(report_path.read_text(encoding="utf-8"))
        slugs: list[str] = []
        for r in data.get("results", []):
            if r.get("ok") and r.get("slug") and r["slug"] != "_":
                slugs.append(str(r["slug"]))
        if slugs:
            return slugs
    slugs = []
    for p in sorted(embed_dir.iterdir()):
        if p.is_dir() and (p / "embedded_chunks.json").is_file():
            slugs.append(p.name)
    return slugs


def _load_embedded_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _corpus_version_hash(pairs: list[tuple[str, str]]) -> str:
    lines = [f"{a}:{b}" for a, b in sorted(pairs)]
    raw = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_embed_corpus_manifest(embed_dir: Path) -> dict[str, Any] | None:
    path = embed_dir / "corpus-manifest.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def run_chroma_ingest(
    embed_input: Path | None = None,
    report_dir: Path | None = None,
) -> ChromaRunReport:
    embed_input = embed_input or DEFAULT_EMBED_OUTPUT
    report_dir = report_dir or DEFAULT_REPORT_OUTPUT
    started = datetime.now(timezone.utc)
    report_dir.mkdir(parents=True, exist_ok=True)

    out_report = ChromaRunReport(
        started_at=started.isoformat(),
        finished_at="",
        embed_input=embed_input.resolve(),
        deployment="not_run",
        persist_directory=None,
        http_host=None,
        cloud_tenant=None,
        cloud_database=None,
        collection_name=COLLECTION_NAME,
        embedding_dim=EMBEDDING_DIM,
        corpus_version="",
        chroma_upserted=0,
        embed_corpus_manifest=_load_embed_corpus_manifest(embed_input.resolve()),
        results=[],
    )

    slugs = _discover_slugs(embed_input)
    out_report.slugs_total = len(slugs)
    if not slugs:
        out_report.finished_at = datetime.now(timezone.utc).isoformat()
        out_report.results.append(
            ChromaIngestResult(slug="_", ok=False, error="no embedded_chunks slugs found")
        )
        _write_reports(report_dir, out_report)
        return out_report

    client, deployment, persist_dir, http_host, cloud_tenant, cloud_database = _make_client()
    out_report.deployment = deployment
    out_report.persist_directory = persist_dir
    out_report.http_host = http_host
    out_report.cloud_tenant = cloud_tenant
    out_report.cloud_database = cloud_database

    if RECREATE_COLLECTION:
        try:
            client.delete_collection(COLLECTION_NAME)
            logger.info("deleted collection %s", COLLECTION_NAME)
        except Exception:
            logger.info("no existing collection %s to delete", COLLECTION_NAME)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    all_ids: list[str] = []
    all_embeddings: list[list[float]] = []
    all_documents: list[str] = []
    all_metadatas: list[dict[str, Any]] = []
    version_pairs: list[tuple[str, str]] = []

    for slug in slugs:
        path = embed_input / slug / "embedded_chunks.json"
        if not path.is_file():
            out_report.results.append(
                ChromaIngestResult(slug=slug, ok=False, error="missing embedded_chunks.json")
            )
            continue
        doc = _load_embedded_file(path)
        if not doc:
            out_report.results.append(
                ChromaIngestResult(slug=slug, ok=False, error="invalid embedded_chunks.json")
            )
            continue
        chunks = doc.get("chunks") or []
        out_report.chunks_total += len(chunks)
        if not chunks:
            out_report.results.append(ChromaIngestResult(slug=slug, ok=False, error="no chunks"))
            continue

        bid: list[str] = []
        bem: list[list[float]] = []
        bdoc: list[str] = []
        bmeta: list[dict[str, Any]] = []
        vpairs: list[tuple[str, str]] = []
        slug_ok = True
        for ch in chunks:
            cid = ch.get("chunk_id")
            emb = ch.get("embedding")
            text = ch.get("text") or ""
            if not cid or not emb or len(emb) != EMBEDDING_DIM:
                out_report.chunk_row_errors += 1
                out_report.results.append(
                    ChromaIngestResult(
                        slug=slug,
                        ok=False,
                        error=f"bad chunk row chunk_id={cid} emb_len={len(emb) if emb else 0}",
                    )
                )
                slug_ok = False
                break
            bid.append(str(cid))
            bem.append([float(x) for x in emb])
            bdoc.append(str(text))
            bmeta.append(chroma_metadata(ch, doc, slug))
            vpairs.append((str(cid), str(ch.get("content_hash") or "")))

        if not slug_ok:
            continue
        if not bid:
            out_report.results.append(ChromaIngestResult(slug=slug, ok=False, error="zero rows"))
            continue
        all_ids.extend(bid)
        all_embeddings.extend(bem)
        all_documents.extend(bdoc)
        all_metadatas.extend(bmeta)
        version_pairs.extend(vpairs)
        out_report.results.append(ChromaIngestResult(slug=slug, ok=True, rows=len(bid)))

    out_report.slugs_succeeded = sum(
        1 for r in out_report.results if r.ok and r.slug not in ("_", "")
    )
    out_report.slugs_failed = sum(
        1 for r in out_report.results if not r.ok and r.slug not in ("_", "")
    )

    failed = [r for r in out_report.results if not r.ok]
    if failed and STRICT:
        out_report.corpus_version = ""
        out_report.finished_at = datetime.now(timezone.utc).isoformat()
        _write_reports(report_dir, out_report)
        return out_report

    if not all_ids:
        out_report.corpus_version = ""
        out_report.finished_at = datetime.now(timezone.utc).isoformat()
        _write_reports(report_dir, out_report)
        return out_report

    _t_upsert = time.perf_counter()
    collection.upsert(
        ids=all_ids,
        embeddings=all_embeddings,
        documents=all_documents,
        metadatas=all_metadatas,
    )
    out_report.chroma_upsert_duration_ms = (time.perf_counter() - _t_upsert) * 1000.0
    out_report.chroma_upserted = len(all_ids)

    manifest_n = (
        out_report.embed_corpus_manifest.get("chunk_count")
        if out_report.embed_corpus_manifest
        else None
    )
    if manifest_n is not None and int(manifest_n) != out_report.chroma_upserted:
        logger.warning(
            "corpus-manifest chunk_count=%s but chroma_upserted=%s (check Phase 4.5 vs 4.6 inputs)",
            manifest_n,
            out_report.chroma_upserted,
        )
    out_report.corpus_version = _corpus_version_hash(version_pairs)
    out_report.finished_at = datetime.now(timezone.utc).isoformat()

    logger.info("Chroma upserted %s rows into %s", len(all_ids), COLLECTION_NAME)
    _write_reports(report_dir, out_report)
    return out_report


def _write_reports(report_dir: Path, report: ChromaRunReport) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "chroma-ingest-report.json").write_text(
        json.dumps(report.to_json(), indent=2),
        encoding="utf-8",
    )
    if report.corpus_version:
        (report_dir / "corpus-version.txt").write_text(
            report.corpus_version + "\n",
            encoding="utf-8",
        )


def exit_code_for_report(report: ChromaRunReport) -> int:
    if any(not r.ok for r in report.results) and STRICT:
        return 1
    if report.chroma_upserted == 0:
        return 1
    return 0
