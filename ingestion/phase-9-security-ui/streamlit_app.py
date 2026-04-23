from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

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


def _new_thread() -> dict:
    tid = str(uuid.uuid4())
    return {
        "id": tid,
        "title": "New Chat",
        "messages": [{"role": "assistant", "text": "How may I help you?"}],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _ensure_state() -> None:
    if "threads" not in st.session_state:
        first = _new_thread()
        st.session_state.threads = {first["id"]: first}
        st.session_state.active_thread_id = first["id"]


def _active_thread() -> dict:
    tid = st.session_state.active_thread_id
    return st.session_state.threads[tid]


def _start_new_chat() -> None:
    t = _new_thread()
    st.session_state.threads[t["id"]] = t
    st.session_state.active_thread_id = t["id"]


def _ask_backend(user_message: str) -> str:
    thread = _active_thread()
    thread_id = thread["id"]
    msg_hash = hash_text(user_message)
    client_ip = "127.0.0.1"

    if contains_pii(user_message):
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "blocked_pii_streamlit",
                "client_ip": client_ip,
                "message_hash": msg_hash,
            }
        )
        return "Please do not share personal identifiers (PAN/Aadhaar/account/OTP/email/phone). Ask a facts-only mutual fund question instead."

    if is_harmful(user_message):
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "blocked_harmful_streamlit",
                "client_ip": client_ip,
                "message_hash": msg_hash,
            }
        )
        return "I can't help with harmful or illegal requests."

    clean_message = redact_text(user_message)
    inj = has_prompt_injection_markers(clean_message)
    if inj:
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "prompt_injection_marker_streamlit",
                "client_ip": client_ip,
                "message_hash": msg_hash,
            }
        )

    try:
        result = run_chat_turn(thread_id=thread_id, user_message=clean_message, client_ip=client_ip)
        payload = result.to_json()
        payload["injection_marker_detected"] = inj
        payload["served_at"] = datetime.now(timezone.utc).isoformat()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "runtime-last.json").write_text(
            __import__("json").dumps(payload, indent=2), encoding="utf-8"
        )
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "chat_ok_streamlit",
                "client_ip": client_ip,
                "message_hash": msg_hash,
                "decision": payload.get("decision"),
            }
        )
        return str(payload.get("answer") or "No answer generated.")
    except Exception as exc:
        append_security_log(
            {
                "thread_id": thread_id,
                "event": "chat_runtime_error_streamlit",
                "client_ip": client_ip,
                "message_hash": msg_hash,
                "error": str(exc),
            }
        )
        return "I am temporarily unavailable. Please try again in a few seconds."


def main() -> None:
    st.set_page_config(page_title="Groww Assistant", page_icon="💬", layout="wide")
    _ensure_state()

    st.title("Groww Assistant")
    st.caption("Facts-only mutual fund assistant. No investment advice.")

    with st.sidebar:
        st.subheader("Threads")
        if st.button("➕ New Chat", use_container_width=True):
            _start_new_chat()

        for tid, thread in reversed(list(st.session_state.threads.items())):
            title = thread["title"] or "New Chat"
            if st.button(title[:38], key=f"thread-{tid}", use_container_width=True):
                st.session_state.active_thread_id = tid

    thread = _active_thread()
    st.markdown(f"**Active thread:** `{thread['id']}`")

    for row in thread["messages"]:
        with st.chat_message("assistant" if row["role"] == "assistant" else "user"):
            st.markdown(row["text"])

    prompt = st.chat_input("Ask a facts-only mutual fund question...")
    if prompt:
        prompt = prompt.strip()
        if prompt:
            thread["messages"].append({"role": "user", "text": prompt})
            if thread["title"] == "New Chat":
                thread["title"] = prompt[:32]
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = _ask_backend(prompt)
                st.markdown(answer)
            thread["messages"].append({"role": "assistant", "text": answer})
            st.rerun()


if __name__ == "__main__":
    main()

