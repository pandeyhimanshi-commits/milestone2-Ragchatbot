from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from embed_service.config import DEFAULT_CHUNK_INPUT, DEFAULT_EMBED_OUTPUT, STRICT
from embed_service.runner import exit_code_for_report, run_embed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Phase 4.5 — embed chunk texts with BAAI/bge-small-en-v1.5 (docs/rag-architecture.md §4.5).",
    )
    p.add_argument(
        "--chunk-input",
        type=Path,
        default=DEFAULT_CHUNK_INPUT,
        help="Phase 4.4 output directory (contains <slug>/chunks.json)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_EMBED_OUTPUT,
        help="Directory for <slug>/embedded_chunks.json",
    )
    args = p.parse_args()
    report = run_embed(chunk_input=args.chunk_input, embed_output=args.output)
    code = exit_code_for_report(report)
    if code != 0:
        logging.error("Embedding finished with errors (EMBED_STRICT=%s)", STRICT)
    sys.exit(code)


if __name__ == "__main__":
    main()
