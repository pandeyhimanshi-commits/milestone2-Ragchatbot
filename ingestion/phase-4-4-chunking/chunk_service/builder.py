from __future__ import annotations

import hashlib
import re
from typing import Any

from chunk_service.config import DOC_TYPE, SECTION_PATH, SPLIT_SENTENCES


def approximate_token_count(text: str) -> int:
    """Rough token estimate (~chars/4) for logging; no external tokenizer in Phase 1."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _stable_chunk_id(source_url: str, section_path: str, chunk_index: int) -> str:
    raw = f"{source_url}\n{section_path}\n{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def build_chunk_records(metrics_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build pre-embedding chunk list from one metrics.json payload.
    See chunking-embedding-architecture.md §3.5.
    """
    source_url = metrics_doc.get("source_url") or ""
    fetched_at = metrics_doc.get("fetched_at") or ""
    retrieval = (metrics_doc.get("retrieval_text") or "").strip()
    if not retrieval:
        return []

    texts: list[str]
    if SPLIT_SENTENCES:
        texts = _split_sentences(retrieval)
        if not texts:
            texts = [retrieval]
    else:
        texts = [retrieval]

    records: list[dict[str, Any]] = []
    for idx, text in enumerate(texts):
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        chunk_id = _stable_chunk_id(source_url, SECTION_PATH, idx)
        records.append(
            {
                "chunk_id": chunk_id,
                "source_url": source_url,
                "fetched_at": fetched_at,
                "doc_type": DOC_TYPE,
                "section_path": SECTION_PATH,
                "chunk_index": idx,
                "text": text,
                "content_hash": content_hash,
                "token_count": approximate_token_count(text),
            }
        )
    return records
