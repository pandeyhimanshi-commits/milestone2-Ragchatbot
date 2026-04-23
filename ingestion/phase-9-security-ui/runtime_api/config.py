from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PHASE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PHASE_ROOT.parent.parent
PHASE7_ROOT = REPO_ROOT / "ingestion" / "phase-7-threading"

for _dotenv_path in (PHASE_ROOT / ".env", REPO_ROOT / ".env"):
    if _dotenv_path.is_file():
        load_dotenv(_dotenv_path, override=False)

HOST = os.environ.get("RUNTIME_HOST", "127.0.0.1")
PORT = int(os.environ.get("RUNTIME_PORT", "8080"))
OUTPUT_DIR = Path(os.environ.get("RUNTIME_OUTPUT_DIR", str(PHASE_ROOT / "output")))
SECURITY_LOG_PATH = Path(
    os.environ.get("RUNTIME_SECURITY_LOG_PATH", str(OUTPUT_DIR / "security-log.jsonl"))
)
