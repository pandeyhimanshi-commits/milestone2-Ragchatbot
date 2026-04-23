from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from embed_service.config import EMBED_BATCH_SIZE, EMBEDDING_MODEL_ID

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("loading %s", EMBEDDING_MODEL_ID)
        _model = SentenceTransformer(EMBEDDING_MODEL_ID)
    return _model


def embedding_dimension() -> int:
    m = get_model()
    fn = getattr(m, "get_embedding_dimension", None) or getattr(
        m, "get_sentence_embedding_dimension"
    )
    return int(fn())


def encode_passages(texts: list[str]) -> np.ndarray:
    """
    Encode corpus passages (chunk texts). BGE uses plain sentences for the
    document side; query-time encoding should use the query prompt (runtime).
    """
    if not texts:
        return np.array([])
    model = get_model()
    # normalize_embeddings=True for cosine similarity in vector DB / retrieval
    emb = model.encode(
        texts,
        batch_size=EMBED_BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 16,
        convert_to_numpy=True,
    )
    return np.asarray(emb, dtype=np.float32)


def vectors_to_jsonable(emb: np.ndarray) -> list[list[float]]:
    return emb.tolist()
