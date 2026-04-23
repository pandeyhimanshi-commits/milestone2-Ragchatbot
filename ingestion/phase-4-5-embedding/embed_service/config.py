from __future__ import annotations

import os
from pathlib import Path

PHASE_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CHUNK_INPUT = Path(
    os.environ.get(
        "EMBED_CHUNK_INPUT",
        str(PHASE_ROOT.parent / "phase-4-4-chunking" / "output"),
    )
)
DEFAULT_EMBED_OUTPUT = Path(
    os.environ.get(
        "EMBED_OUTPUT_DIR",
        str(PHASE_ROOT / "output"),
    )
)

# Corpus / passage side (not query prefix) — see BGE model card
EMBEDDING_MODEL_ID = os.environ.get(
    "EMBEDDING_MODEL_ID",
    "BAAI/bge-small-en-v1.5",
)

EMBEDDING_VERSION = int(os.environ.get("EMBEDDING_VERSION", "1"))
EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "32"))
STRICT = os.environ.get("EMBED_STRICT", "0").lower() in ("1", "true", "yes")
