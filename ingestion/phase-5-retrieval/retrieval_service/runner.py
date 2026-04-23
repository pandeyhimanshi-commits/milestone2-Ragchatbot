from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb

from retrieval_service.config import (
    ALLOWLIST_PATH,
    CHROMA_API_KEY,
    CHROMA_CLOUD_DATABASE,
    CHROMA_CLOUD_TENANT,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    CHROMA_PERSIST_DIRECTORY,
    COLLECTION_NAME,
    CONFIDENCE_DISTANCE_THRESHOLD,
    EMBEDDING_DIM,
    GROUNDING_TOP_K,
    OUTPUT_PATH,
    RETRIEVE_WRITE_LAST_JSON,
    QUERY_TOP_K,
    THREAD_HISTORY_LIMIT,
    THREAD_STORE_PATH,
)
from retrieval_service.encoder import encode_query
from retrieval_service.thread_store import ThreadState, ThreadStore

logger = logging.getLogger(__name__)

# Reuse one Chroma client + collection per process (avoids reconnect + metadata fetch each request).
_chroma_lock = threading.Lock()
_chroma_collection: Any = None

# Allowlist is static for a running process unless the file changes (rare).
_allowlist_cache: tuple[float | None, list[str]] | None = None

TERM_EXPANSIONS: dict[str, str] = {
    "ter": "expense ratio",
    "aum": "fund size",
    "nav": "net asset value",
    "sip": "minimum sip",
}


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None


@dataclass
class RetrievalResponse:
    decision: str
    query: str
    query_expanded: str
    thread_id: str
    scheme_slug: str | None
    citation_url: str | None
    confidence_best_distance: float | None
    message: str | None
    retrieved: list[RetrievedChunk] = field(default_factory=list)
    grounded: list[RetrievedChunk] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "query": self.query,
            "query_expanded": self.query_expanded,
            "thread_id": self.thread_id,
            "scheme_slug": self.scheme_slug,
            "citation_url": self.citation_url,
            "confidence_best_distance": self.confidence_best_distance,
            "message": self.message,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "retrieved": [
                {
                    "chunk_id": r.chunk_id,
                    "text": r.text,
                    "metadata": r.metadata,
                    "distance": r.distance,
                }
                for r in self.retrieved
            ],
            "grounded": [
                {
                    "chunk_id": r.chunk_id,
                    "text": r.text,
                    "metadata": r.metadata,
                    "distance": r.distance,
                }
                for r in self.grounded
            ],
        }


def _make_client() -> chromadb.ClientAPI:
    if CHROMA_CLOUD_TENANT and CHROMA_CLOUD_DATABASE:
        logger.info(
            "retrieval using Chroma Cloud tenant=%s database=%s",
            CHROMA_CLOUD_TENANT,
            CHROMA_CLOUD_DATABASE,
        )
        return chromadb.CloudClient(
            tenant=CHROMA_CLOUD_TENANT,
            database=CHROMA_CLOUD_DATABASE,
            api_key=(CHROMA_API_KEY or None),
        )
    if CHROMA_HTTP_HOST:
        logger.info("retrieval using Chroma HttpClient %s:%s", CHROMA_HTTP_HOST, CHROMA_HTTP_PORT)
        return chromadb.HttpClient(host=CHROMA_HTTP_HOST, port=CHROMA_HTTP_PORT)
    logger.info("retrieval using Chroma PersistentClient %s", CHROMA_PERSIST_DIRECTORY)
    return chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIRECTORY))


def _get_chroma_collection():
    """Return a process-wide cached collection handle (first call logs + connects)."""
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    with _chroma_lock:
        if _chroma_collection is not None:
            return _chroma_collection
        client = _make_client()
        _chroma_collection = client.get_collection(COLLECTION_NAME)
        return _chroma_collection


def _load_allowlist_urls(path: Path) -> list[str]:
    global _allowlist_cache
    if not path.is_file():
        return []
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return []
    if _allowlist_cache is not None and _allowlist_cache[0] == mtime:
        return _allowlist_cache[1]
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if t.startswith("- http://") or t.startswith("- https://"):
            out.append(t[2:].strip())
    _allowlist_cache = (mtime, out)
    return out


def _expand_query(q: str) -> str:
    base = q.strip()
    low = f" {base.lower()} "
    extras: list[str] = []
    for token, expansion in TERM_EXPANSIONS.items():
        if f" {token} " in low or low.startswith(f"{token} ") or low.endswith(f" {token}"):
            extras.append(expansion)
    if not extras:
        return base
    return f"{base}. Related terms: {', '.join(sorted(set(extras)))}."


def _slug_candidates_from_query(query: str, urls: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    q = query.lower()
    generic_tokens = {"hdfc", "fund", "direct", "growth", "plan", "mutual"}
    for u in urls:
        slug = u.rstrip("/").split("/")[-1]
        scheme_hint = slug.replace("-", " ")
        tokens = [tok for tok in scheme_hint.split() if len(tok) > 3 and tok not in generic_tokens]
        # Require specific signal tokens (e.g. "mid", "elss", "equity"), not just "hdfc fund".
        if tokens and any(tok in q for tok in tokens):
            out[slug] = u
    return out


def _dedupe_chunks(rows: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for r in rows:
        key = f"{r.metadata.get('source_url','')}||{r.text.strip()}"
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def run_retrieval(query: str, thread_id: str, top_k: int = QUERY_TOP_K) -> RetrievalResponse:
    started = datetime.now(timezone.utc)
    store = ThreadStore(path=THREAD_STORE_PATH, history_limit=THREAD_HISTORY_LIMIT)
    state = store.get(thread_id)
    urls = _load_allowlist_urls(ALLOWLIST_PATH)
    candidates = _slug_candidates_from_query(query, urls)

    resolved_slug = next(iter(candidates), None) or state.scheme_slug
    expanded = _expand_query(query)
    query_vec = encode_query(expanded)
    if len(query_vec) != EMBEDDING_DIM:
        raise ValueError(f"query embedding dim mismatch: got {len(query_vec)} expected {EMBEDDING_DIM}")

    collection = _get_chroma_collection()
    where = {"slug": resolved_slug} if resolved_slug else None

    raw = collection.query(
        query_embeddings=[query_vec],
        n_results=max(1, top_k),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]
    ids = (raw.get("ids") or [[]])[0]

    rows: list[RetrievedChunk] = []
    for i, doc in enumerate(docs):
        md = (metas[i] if i < len(metas) and metas[i] is not None else {}) or {}
        dist = float(dists[i]) if i < len(dists) and dists[i] is not None else None
        cid = str(ids[i]) if i < len(ids) else str(md.get("chunk_id") or "")
        rows.append(
            RetrievedChunk(
                chunk_id=cid,
                text=str(doc or ""),
                metadata={str(k): v for k, v in md.items()},
                distance=dist,
            )
        )
    rows = _dedupe_chunks(rows)

    best = min((r.distance for r in rows if r.distance is not None), default=None)
    grounded = rows[: max(1, GROUNDING_TOP_K)]
    citation_url = str(grounded[0].metadata.get("source_url")) if grounded else None
    fallback_url = citation_url or (candidates.get(resolved_slug or "", "") if resolved_slug else "") or (
        urls[0] if urls else None
    )

    if not rows or best is None or best > CONFIDENCE_DISTANCE_THRESHOLD:
        response = RetrievalResponse(
            decision="insufficient_evidence",
            query=query,
            query_expanded=expanded,
            thread_id=thread_id,
            scheme_slug=resolved_slug,
            citation_url=fallback_url,
            confidence_best_distance=best,
            message="I couldn't find this in the indexed official sources.",
            retrieved=rows,
            grounded=grounded,
        )
    else:
        response = RetrievalResponse(
            decision="answer",
            query=query,
            query_expanded=expanded,
            thread_id=thread_id,
            scheme_slug=resolved_slug,
            citation_url=citation_url,
            confidence_best_distance=best,
            message=None,
            retrieved=rows,
            grounded=grounded,
        )

    state.history.append(query.strip())
    state.history = state.history[-THREAD_HISTORY_LIMIT:]
    if resolved_slug:
        state.scheme_slug = resolved_slug
    store.put(state)

    response.finished_at = datetime.now(timezone.utc).isoformat()
    if RETRIEVE_WRITE_LAST_JSON:
        OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        (OUTPUT_PATH / "retrieval-last.json").write_text(
            json.dumps(response.to_json(), indent=2),
            encoding="utf-8",
        )
    return response


def seed_thread(thread_id: str, scheme_slug: str | None = None) -> ThreadState:
    store = ThreadStore(path=THREAD_STORE_PATH, history_limit=THREAD_HISTORY_LIMIT)
    state = store.get(thread_id)
    state.scheme_slug = scheme_slug
    store.put(state)
    return state

