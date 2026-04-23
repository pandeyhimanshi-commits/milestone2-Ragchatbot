from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Reduce noisy telemetry client errors in some environments (optional).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from chroma_service.config import DEFAULT_EMBED_OUTPUT, DEFAULT_REPORT_OUTPUT, STRICT
from chroma_service.runner import exit_code_for_report, run_chroma_ingest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Phase 4.6 — upsert embedded chunks into Chroma (docs/rag-architecture.md §4.6).",
    )
    p.add_argument(
        "--embed-input",
        type=Path,
        default=DEFAULT_EMBED_OUTPUT,
        help="Phase 4.5 output directory",
    )
    p.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help="Directory for chroma-ingest-report.json and corpus-version.txt",
    )
    args = p.parse_args()
    report = run_chroma_ingest(embed_input=args.embed_input, report_dir=args.report_dir)
    code = exit_code_for_report(report)
    if code != 0:
        logging.error("Chroma ingest finished with errors (CHROMA_STRICT=%s)", STRICT)
    sys.exit(code)


if __name__ == "__main__":
    main()
