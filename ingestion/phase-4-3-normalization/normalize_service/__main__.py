from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from normalize_service.config import DEFAULT_NORMALIZE_OUTPUT, DEFAULT_SCRAPE_OUTPUT, STRICT
from normalize_service.runner import exit_code_for_report, run_normalize


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Phase 4.3 — extract NAV, minimum SIP, fund size (AUM), expense ratio, Groww rating; store metrics.json only.",
    )
    p.add_argument(
        "--scrape-output",
        type=Path,
        default=DEFAULT_SCRAPE_OUTPUT,
        help="Directory containing scrape run (run-report.json and <slug>/body.html)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_NORMALIZE_OUTPUT,
        help="Directory for <slug>/metrics.json",
    )
    args = p.parse_args()
    report = run_normalize(scrape_output=args.scrape_output, normalize_output=args.output)
    code = exit_code_for_report(report)
    if code != 0:
        logging.error("Normalization finished with errors (NORMALIZE_STRICT=%s)", STRICT)
    sys.exit(code)


if __name__ == "__main__":
    main()
