from __future__ import annotations

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from retrieval_service.config import EMBEDDING_MODEL_ID, QUERY_PROMPT_PREFIX

logger = logging.getLogger(__name__)
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("loading retrieval model %s", EMBEDDING_MODEL_ID)
        _model = SentenceTransformer(EMBEDDING_MODEL_ID)
    return _model


def encode_query(query: str) -> list[float]:
    model = get_model()
    q = f"{QUERY_PROMPT_PREFIX}{query.strip()}"
    emb = model.encode(
        [q],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    row = np.asarray(emb[0], dtype=np.float32)
    return row.tolist()

