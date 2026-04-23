from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid

from threading_service.runner import run_chat_turn


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        # Keep CLI usable on cp1252 terminals (Windows default) when model emits ₹, etc.
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Phase 7 multi-thread turn runner (docs/rag-architecture.md §7).",
    )
    p.add_argument("--thread-id", type=str, default=str(uuid.uuid4()), help="Opaque thread id")
    p.add_argument("--message", type=str, required=True, help="User message")
    p.add_argument("--client-ip", type=str, default="127.0.0.1", help="Client IP for rate limit")
    p.add_argument("--json", action="store_true", help="Print full JSON result")
    args = p.parse_args()

    try:
        result = run_chat_turn(thread_id=args.thread_id, user_message=args.message, client_ip=args.client_ip)
    except Exception as exc:
        _safe_print(f"thread_id: {args.thread_id}")
        _safe_print("decision: temporarily_unavailable")
        _safe_print(f"I am temporarily unavailable: {type(exc).__name__}")
        sys.exit(0)
    if args.json:
        _safe_print(json.dumps(result.to_json(), indent=2))
    else:
        _safe_print(f"thread_id: {result.thread_id}")
        _safe_print(f"decision: {result.decision}")
        _safe_print(result.answer)
    sys.exit(0)


if __name__ == "__main__":
    main()

