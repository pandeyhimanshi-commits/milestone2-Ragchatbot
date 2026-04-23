from __future__ import annotations

from typing import Any


def chroma_metadata(
    chunk: dict[str, Any],
    parent: dict[str, Any],
    slug: str,
) -> dict[str, Any]:
    """Flatten to Chroma-allowed types: str, int, float, bool (no None)."""
    out: dict[str, Any] = {
        "slug": str(slug),
        "chunk_id": str(chunk.get("chunk_id") or ""),
        "source_url": str(chunk.get("source_url") or parent.get("source_url") or ""),
        "scheme_name": str(parent.get("scheme_name") or ""),
        "fetched_at": str(chunk.get("fetched_at") or ""),
        "content_hash": str(chunk.get("content_hash") or ""),
        "doc_type": str(chunk.get("doc_type") or parent.get("doc_type") or ""),
        "section_path": str(chunk.get("section_path") or ""),
        "embedding_model_id": str(chunk.get("embedding_model_id") or ""),
        "embedded_at": str(chunk.get("embedded_at") or ""),
    }
    ci = chunk.get("chunk_index")
    if ci is not None:
        try:
            out["chunk_index"] = int(ci)
        except (TypeError, ValueError):
            out["chunk_index"] = 0
    ed = chunk.get("embedding_dim")
    if ed is not None:
        try:
            out["embedding_dim"] = int(ed)
        except (TypeError, ValueError):
            pass
    return {
        k: v
        for k, v in out.items()
        if v is not None and (not isinstance(v, str) or v != "")
    }
