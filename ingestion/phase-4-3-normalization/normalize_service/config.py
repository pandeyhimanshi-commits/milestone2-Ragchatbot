from __future__ import annotations

import os
from pathlib import Path

PHASE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCRAPE_OUTPUT = Path(
    os.environ.get(
        "NORMALIZE_SCRAPE_OUTPUT",
        str(PHASE_ROOT.parent / "phase-4-2-scraping" / "output"),
    )
)
DEFAULT_NORMALIZE_OUTPUT = Path(
    os.environ.get(
        "NORMALIZE_OUTPUT_DIR",
        str(PHASE_ROOT / "output"),
    )
)

NORMALIZE_VERSION = int(os.environ.get("NORMALIZE_VERSION", "2"))
STRICT = os.environ.get("NORMALIZE_STRICT", "0").lower() in ("1", "true", "yes")

# Phase 1: only key metrics persisted (docs/rag-architecture.md §3.3 / §4.3)
DOC_TYPE = "groww_scheme_metrics"
SCHEMA_VERSION = 2
