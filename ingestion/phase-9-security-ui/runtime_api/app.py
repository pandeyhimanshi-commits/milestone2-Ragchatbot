from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from runtime_api.config import OUTPUT_DIR, PHASE7_ROOT
from runtime_api.security import (
    append_security_log,
    contains_pii,
    has_prompt_injection_markers,
    hash_text,
    is_harmful,
    redact_text,
)

PHASE5_ROOT = PHASE7_ROOT.parent / "phase-5-retrieval"

# Do not import threading/retrieval/generation at module load. That pulls in sentence-transformers,
# torch, chroma, and Gemini in one go and often OOMs or times out on Render before any port opens.
# Heavy imports are lazy-loaded on first /chat (and optional warmup).
_run_chat_turn: Callable[..., Any] | None = None


def _ensure_rag_path() -> None:
    p5, p7 = str(PHASE5_ROOT), str(PHASE7_ROOT)
    if p5 not in sys.path:
        sys.path.insert(0, p5)
    if p7 not in sys.path:
        sys.path.insert(0, p7)


def get_run_chat_turn() -> Any:
    global _run_chat_turn
    if _run_chat_turn is None:
        _ensure_rag_path()
        from threading_service.runner import run_chat_turn  # type: ignore  # noqa: E402

        _run_chat_turn = run_chat_turn
    return _run_chat_turn

app = FastAPI(title="MF FAQ Runtime API", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

cors_allow_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*").strip()
origins = (
    [origin.strip() for origin in cors_allow_origins.split(",") if origin.strip()]
    if cors_allow_origins
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    thread_id: str | None = None
    message: str
    client_ip: str | None = None


@app.on_event("startup")
def warmup_models() -> None:
    # On Render and small instances, skipping warmup avoids startup timeouts and high RAM spikes.
    skip_warmup = os.environ.get("SKIP_MODEL_WARMUP", "").strip().lower() in ("1", "true", "yes")
    if not os.environ.get("SKIP_MODEL_WARMUP") and os.environ.get("RENDER") == "true":
        skip_warmup = True
    if skip_warmup:
        return
    _ensure_rag_path()
    try:
        from retrieval_service.encoder import encode_query, get_model  # type: ignore  # noqa: E402

        get_model()
        encode_query("warmup: HDFC mutual fund scheme metrics")
    except Exception:
        # Keep API boot resilient even if warmup fails.
        pass


@app.get("/")
def ui_index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest, request: Request) -> JSONResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    msg = req.message.strip()
    client_ip = req.client_ip or (request.client.host if request.client else "127.0.0.1")
    msg_hash = hash_text(msg)

    if not msg:
        return JSONResponse(status_code=400, content={"error": "message cannot be empty"})

    if contains_pii(msg):
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "blocked_pii",
                "client_ip": client_ip,
                "message_hash": msg_hash,
            }
        )
        return JSONResponse(
            status_code=400,
            content={
                "thread_id": thread_id,
                "decision": "blocked",
                "answer": "Please do not share personal identifiers (PAN/Aadhaar/account/OTP/email/phone). Ask a facts-only mutual fund question instead.",
            },
        )

    if is_harmful(msg):
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "blocked_harmful",
                "client_ip": client_ip,
                "message_hash": msg_hash,
            }
        )
        return JSONResponse(
            status_code=400,
            content={
                "thread_id": thread_id,
                "decision": "blocked",
                "answer": "I can't help with harmful or illegal requests.",
            },
        )

    clean_message = redact_text(msg)
    inj = has_prompt_injection_markers(clean_message)
    if inj:
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "prompt_injection_marker",
                "client_ip": client_ip,
                "message_hash": msg_hash,
            }
        )

    try:
        result = get_run_chat_turn()(
            thread_id=thread_id, user_message=clean_message, client_ip=client_ip
        )
    except Exception as e:
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "chat_runtime_error",
                "client_ip": client_ip,
                "message_hash": msg_hash,
                "error": str(e),
            }
        )
        # Graceful degradation for transient LLM/provider failures.
        return JSONResponse(
            status_code=200,
            content={
                "thread_id": thread_id,
                "decision": "temporarily_unavailable",
                "answer": "I am temporarily unavailable. Please try again in a few seconds.",
            },
        )
    payload: dict[str, Any] = result.to_json()
    payload["injection_marker_detected"] = inj
    payload["served_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "runtime-last.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    append_security_log(
        {
            "thread_id": thread_id,
            "event": "chat_ok",
            "client_ip": client_ip,
            "message_hash": msg_hash,
            "decision": payload.get("decision"),
        }
    )
    return JSONResponse(content=payload)

