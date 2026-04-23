from __future__ import annotations

import os
from pathlib import Path

PHASE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_METRICS_OUTPUT = Path(
    os.environ.get(
        "CHUNK_METRICS_INPUT",
        str(PHASE_ROOT.parent / "phase-4-3-normalization" / "output"),
    )
)
DEFAULT_CHUNK_OUTPUT = Path(
    os.environ.get(
        "CHUNK_OUTPUT_DIR",
        str(PHASE_ROOT / "output"),
    )
)

CHUNKING_VERSION = int(os.environ.get("CHUNKING_VERSION", "1"))
STRICT = os.environ.get("CHUNK_STRICT", "0").lower() in ("1", "true", "yes")

DOC_TYPE = "groww_scheme_metrics"
SECTION_PATH = os.environ.get("CHUNK_SECTION_PATH", "Key metrics")

# Phase 1 default: one chunk per scheme from full retrieval_text
SPLIT_SENTENCES = os.environ.get("CHUNK_SPLIT_SENTENCES", "0").lower() in ("1", "true", "yes")
