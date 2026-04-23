from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PHASE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PHASE_ROOT.parent.parent
PHASE5_ROOT = REPO_ROOT / "ingestion" / "phase-5-retrieval"
PHASE43_ROOT = REPO_ROOT / "ingestion" / "phase-4-3-normalization"

for _dotenv_path in (PHASE_ROOT / ".env", REPO_ROOT / ".env"):
    if _dotenv_path.is_file():
        load_dotenv(_dotenv_path, override=False)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
REFUSAL_EDUCATIONAL_URL = os.environ.get(
    "REFUSAL_EDUCATIONAL_URL",
    "https://www.amfiindia.com/investor-corner/knowledge-center",
).strip()

MAX_SENTENCES = int(os.environ.get("GEN_MAX_SENTENCES", "3"))
GEN_REPAIR_ONCE = os.environ.get("GEN_REPAIR_ONCE", "1").lower() in ("1", "true", "yes")
OUTPUT_PATH = Path(os.environ.get("GEN_OUTPUT_PATH", str(PHASE_ROOT / "output")))
# Set to 0/false to skip writing generation-last.json each request (lower latency).
GEN_WRITE_LAST_JSON = os.environ.get("GEN_WRITE_LAST_JSON", "1").lower() in ("1", "true", "yes")
