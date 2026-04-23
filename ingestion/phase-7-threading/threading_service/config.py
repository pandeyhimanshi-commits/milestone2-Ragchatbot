from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PHASE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PHASE_ROOT.parent.parent
PHASE6_ROOT = REPO_ROOT / "ingestion" / "phase-6-generation"

for _dotenv_path in (PHASE_ROOT / ".env", REPO_ROOT / ".env"):
    if _dotenv_path.is_file():
        load_dotenv(_dotenv_path, override=False)

OUTPUT_DIR = Path(os.environ.get("THREAD_OUTPUT_DIR", str(PHASE_ROOT / "output")))
THREAD_STATE_PATH = Path(os.environ.get("THREAD_STATE_PATH", str(OUTPUT_DIR / "thread_state.json")))
RATE_LIMIT_STATE_PATH = Path(
    os.environ.get("THREAD_RATE_LIMIT_PATH", str(OUTPUT_DIR / "rate_limit_state.json"))
)

THREAD_HISTORY_LIMIT = int(os.environ.get("THREAD_HISTORY_LIMIT", "8"))
MAX_PARALLEL_PER_THREAD = int(os.environ.get("THREAD_MAX_PARALLEL", "1"))

RATE_LIMIT_PER_THREAD_PER_MIN = int(os.environ.get("THREAD_RATE_PER_MIN", "20"))
RATE_LIMIT_PER_IP_PER_MIN = int(os.environ.get("IP_RATE_PER_MIN", "60"))

ALLOWLIST_PATH = Path(
    os.environ.get(
        "THREAD_ALLOWLIST_PATH",
        str(REPO_ROOT / "ingestion" / "shared" / "allowlist.yaml"),
    )
)
