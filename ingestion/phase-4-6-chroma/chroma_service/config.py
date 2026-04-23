from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PHASE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PHASE_ROOT.parent.parent

for _dotenv_path in (PHASE_ROOT / ".env", REPO_ROOT / ".env"):
    if _dotenv_path.is_file():
        load_dotenv(_dotenv_path, override=False)

# Must be set before `import chromadb` (runner imports this module first).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

DEFAULT_EMBED_OUTPUT = Path(
    os.environ.get(
        "CHROMA_EMBED_INPUT",
        str(PHASE_ROOT.parent / "phase-4-5-embedding" / "output"),
    )
)
DEFAULT_REPORT_OUTPUT = Path(
    os.environ.get(
        "CHROMA_REPORT_DIR",
        str(PHASE_ROOT / "output"),
    )
)
DEFAULT_PERSIST_DIR = Path(
    os.environ.get(
        "CHROMA_PERSIST_DIRECTORY",
        str(PHASE_ROOT / "data" / "chroma_db"),
    )
)

COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "mf_faq_groww_metrics")
EMBEDDING_DIM = int(os.environ.get("CHROMA_EMBEDDING_DIM", "384"))

# If true, always use DEFAULT_PERSIST_DIR (Phase 5 default) even when .env has Cloud — keeps ingest aligned with local retrieval.
CHROMA_USE_PERSISTENT = os.environ.get("CHROMA_USE_PERSISTENT", "").lower() in (
    "1",
    "true",
    "yes",
)

# Chroma Cloud (https://app.trychroma.com) — all three required to use CloudClient
CHROMA_CLOUD_TENANT = os.environ.get("CHROMA_CLOUD_TENANT", "").strip()
CHROMA_CLOUD_DATABASE = os.environ.get("CHROMA_CLOUD_DATABASE", "").strip()
# API key: Chroma reads CHROMA_API_KEY; see https://docs.trychroma.com/docs/run-chroma/clients
CHROMA_API_KEY = os.environ.get("CHROMA_API_KEY", "").strip()

# If set (e.g. localhost), use HttpClient instead of PersistentClient / Cloud
CHROMA_HTTP_HOST = os.environ.get("CHROMA_HTTP_HOST", "").strip()
CHROMA_HTTP_PORT = int(os.environ.get("CHROMA_HTTP_PORT", "8000"))

STRICT = os.environ.get("CHROMA_STRICT", "0").lower() in ("1", "true", "yes")

# Small-corpus shortcut: delete collection then recreate before upsert
RECREATE_COLLECTION = os.environ.get("CHROMA_RECREATE_COLLECTION", "0").lower() in (
    "1",
    "true",
    "yes",
)
