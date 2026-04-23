from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from scrape_service.config import DEFAULT_ALLOWLIST, OUTPUT_DIR, SNAPSHOTS_DIR, STRICT
from scrape_service.fetcher import exit_code_for_report, run_scrape


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    p = argparse.ArgumentParser(description="Phase 4.2 scraping service (allowlisted URLs only).")
    p.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST,
        help="Path to allowlist YAML (default: ingestion/shared/allowlist.yaml)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for body.html + meta.json per slug",
    )
    p.add_argument(
        "--snapshots",
        type=Path,
        default=SNAPSHOTS_DIR,
        help="Snapshot directory (latest good copy per slug)",
    )
    args = p.parse_args()

    report = run_scrape(
        allowlist_path=args.allowlist,
        output_dir=args.output,
        snapshots_dir=args.snapshots,
    )
    code = exit_code_for_report(report)
    if code != 0:
        logging.error("Scrape completed with failures (SCRAPE_STRICT=%s)", STRICT)
    sys.exit(code)


if __name__ == "__main__":
    main()
