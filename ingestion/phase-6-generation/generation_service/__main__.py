from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid

from generation_service.runner import run_generation


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        # Keep CLI usable on cp1252 terminals (Windows default) when model emits ₹, etc.
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Phase 6 generation and guardrails using Gemini (docs/rag-architecture.md §6).",
    )
    parser.add_argument("--query", required=True, type=str, help="User question")
    parser.add_argument(
        "--thread-id",
        type=str,
        default=str(uuid.uuid4()),
        help="Opaque thread identifier",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON response")
    args = parser.parse_args()

    try:
        resp = run_generation(query=args.query, thread_id=args.thread_id)
    except Exception as exc:
        _safe_print(f"thread_id: {args.thread_id}")
        _safe_print("decision: temporarily_unavailable")
        _safe_print(f"I am temporarily unavailable: {type(exc).__name__}")
        sys.exit(0)
    if args.json:
        _safe_print(json.dumps(resp.to_json(), indent=2))
    else:
        _safe_print(f"thread_id: {resp.thread_id}")
        _safe_print(f"decision: {resp.decision}")
        _safe_print(resp.answer)
    sys.exit(0)


if __name__ == "__main__":
    main()

