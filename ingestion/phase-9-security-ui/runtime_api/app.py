from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
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
sys.path.insert(0, str(PHASE5_ROOT))
sys.path.insert(0, str(PHASE7_ROOT))
from threading_service.runner import run_chat_turn  # type: ignore  # noqa: E402
from retrieval_service.encoder import encode_query, get_model  # type: ignore  # noqa: E402

app = FastAPI(title="MF FAQ Runtime API", version="0.1.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatRequest(BaseModel):
    thread_id: str | None = None
    message: str
    client_ip: str | None = None


@app.on_event("startup")
def warmup_models() -> None:
    # Warm the embedding model and one real encode to avoid a multi-second first /chat.
    try:
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
        result = run_chat_turn(thread_id=thread_id, user_message=clean_message, client_ip=client_ip)
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

