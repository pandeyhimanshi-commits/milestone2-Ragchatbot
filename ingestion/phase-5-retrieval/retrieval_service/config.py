from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PHASE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PHASE_ROOT.parent.parent

# Phase 4.6 Chroma often stores CHROMA_CLOUD_* only there; include it so retrieval uses the same Chroma as ingest.
for _dotenv_path in (
    PHASE_ROOT / ".env",
    REPO_ROOT / ".env",
    REPO_ROOT / "ingestion" / "phase-4-6-chroma" / ".env",
):
    if _dotenv_path.is_file():
        load_dotenv(_dotenv_path, override=False)

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

COLLECTION_NAME = os.environ.get("RETRIEVE_COLLECTION_NAME", "mf_faq_groww_metrics")
EMBEDDING_MODEL_ID = os.environ.get("RETRIEVE_EMBEDDING_MODEL_ID", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM = int(os.environ.get("RETRIEVE_EMBEDDING_DIM", "384"))
QUERY_TOP_K = int(os.environ.get("RETRIEVE_TOP_K", "12"))
GROUNDING_TOP_K = int(os.environ.get("RETRIEVE_GROUNDING_TOP_K", "3"))
CONFIDENCE_DISTANCE_THRESHOLD = float(
    os.environ.get("RETRIEVE_CONFIDENCE_DISTANCE_THRESHOLD", "0.35")
)
THREAD_HISTORY_LIMIT = int(os.environ.get("RETRIEVE_THREAD_HISTORY_LIMIT", "8"))
THREAD_STORE_PATH = Path(
    os.environ.get("RETRIEVE_THREAD_STORE_PATH", str(PHASE_ROOT / "output" / "thread_store.json"))
)
OUTPUT_PATH = Path(os.environ.get("RETRIEVE_OUTPUT_PATH", str(PHASE_ROOT / "output")))
# Set to 0/false to skip writing retrieval-last.json each request (lower latency in production).
RETRIEVE_WRITE_LAST_JSON = os.environ.get("RETRIEVE_WRITE_LAST_JSON", "1").lower() in (
    "1",
    "true",
    "yes",
)

# BGE query instruction (runtime/query side).
QUERY_PROMPT_PREFIX = os.environ.get(
    "RETRIEVE_QUERY_PROMPT_PREFIX",
    "Represent this sentence for searching relevant passages: ",
)

CHROMA_CLOUD_TENANT = os.environ.get("CHROMA_CLOUD_TENANT", "").strip()
CHROMA_CLOUD_DATABASE = os.environ.get("CHROMA_CLOUD_DATABASE", "").strip()
CHROMA_API_KEY = os.environ.get("CHROMA_API_KEY", "").strip()
CHROMA_HTTP_HOST = os.environ.get("CHROMA_HTTP_HOST", "").strip()
CHROMA_HTTP_PORT = int(os.environ.get("CHROMA_HTTP_PORT", "8000"))
CHROMA_PERSIST_DIRECTORY = Path(
    os.environ.get(
        "CHROMA_PERSIST_DIRECTORY",
        str(REPO_ROOT / "ingestion" / "phase-4-6-chroma" / "data" / "chroma_db"),
    )
)

ALLOWLIST_PATH = Path(
    os.environ.get(
        "RETRIEVE_ALLOWLIST_PATH",
        str(REPO_ROOT / "ingestion" / "shared" / "allowlist.yaml"),
    )
)
