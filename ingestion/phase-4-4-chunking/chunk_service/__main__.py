from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from chunk_service.config import DEFAULT_CHUNK_OUTPUT, DEFAULT_METRICS_OUTPUT, STRICT
from chunk_service.runner import exit_code_for_report, run_chunking


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Phase 4.4 — build chunk records from metrics.json (docs/rag-architecture.md §4.4).",
    )
    p.add_argument(
        "--metrics-input",
        type=Path,
        default=DEFAULT_METRICS_OUTPUT,
        help="Phase 4.3 output directory (contains <slug>/metrics.json)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CHUNK_OUTPUT,
        help="Directory for <slug>/chunks.json",
    )
    args = p.parse_args()
    report = run_chunking(metrics_input=args.metrics_input, chunk_output=args.output)
    code = exit_code_for_report(report)
    if code != 0:
        logging.error("Chunking finished with errors (CHUNK_STRICT=%s)", STRICT)
    sys.exit(code)


if __name__ == "__main__":
    main()
