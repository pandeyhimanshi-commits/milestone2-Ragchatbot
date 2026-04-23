from __future__ import annotations

import os
from pathlib import Path

# Identifiable UA per architecture §4.2
DEFAULT_USER_AGENT = (
    "MutualFundFAQIngest/1.0 "
    "(+https://github.com/; RAG corpus ingest; contact: repo owner)"
)

REQUEST_TIMEOUT_S = float(os.environ.get("SCRAPE_TIMEOUT_S", "30"))
MAX_RETRIES = int(os.environ.get("SCRAPE_MAX_RETRIES", "3"))
BACKOFF_BASE_S = float(os.environ.get("SCRAPE_BACKOFF_BASE_S", "1.0"))
DELAY_BETWEEN_URLS_S = float(os.environ.get("SCRAPE_DELAY_BETWEEN_URLS_S", "1.0"))

# phase-4-2-scraping/
PHASE_ROOT = Path(__file__).resolve().parent.parent
# ingestion/shared/
SHARED_ROOT = PHASE_ROOT.parent / "shared"
DEFAULT_ALLOWLIST = SHARED_ROOT / "allowlist.yaml"
OUTPUT_DIR = Path(os.environ.get("SCRAPE_OUTPUT_DIR", str(PHASE_ROOT / "output")))
SNAPSHOTS_DIR = Path(os.environ.get("SCRAPE_SNAPSHOTS_DIR", str(PHASE_ROOT / "data" / "snapshots")))

STRICT = os.environ.get("SCRAPE_STRICT", "0").lower() in ("1", "true", "yes")
