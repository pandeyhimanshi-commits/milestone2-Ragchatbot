from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml

from scrape_service.config import (
    BACKOFF_BASE_S,
    DEFAULT_ALLOWLIST,
    DEFAULT_USER_AGENT,
    DELAY_BETWEEN_URLS_S,
    MAX_RETRIES,
    OUTPUT_DIR,
    REQUEST_TIMEOUT_S,
    SNAPSHOTS_DIR,
    STRICT,
)
from scrape_service.robots import RobotsGate

logger = logging.getLogger(__name__)


def url_slug(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    last = path.split("/")[-1] if path else "root"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in last)
    return safe or "page"


def load_allowlist(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    urls = data.get("urls") if isinstance(data, dict) else None
    if not urls or not isinstance(urls, list):
        raise ValueError("allowlist must be a YAML dict with key 'urls' (list)")
    return [str(u) for u in urls]


@dataclass
class UrlResult:
    url: str
    slug: str
    ok: bool
    status_code: int | None
    fetched_at: str
    error: str | None = None
    content_sha256: str | None = None
    bytes_written: int | None = None


@dataclass
class RunReport:
    started_at: str
    finished_at: str
    allowlist: Path
    results: list[UrlResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "allowlist": str(self.allowlist),
            "strict": STRICT,
            "results": [
                {
                    "url": r.url,
                    "slug": r.slug,
                    "ok": r.ok,
                    "status_code": r.status_code,
                    "fetched_at": r.fetched_at,
                    "error": r.error,
                    "content_sha256": r.content_sha256,
                    "bytes_written": r.bytes_written,
                }
                for r in self.results
            ],
        }


def _sleep_backoff(attempt: int) -> None:
    time.sleep(BACKOFF_BASE_S * (2**attempt))


def fetch_url_with_retries(
    client: httpx.Client,
    url: str,
) -> tuple[int | None, bytes | None, str | None]:
    last_err: str | None = None
    for attempt in range(MAX_RETRIES):
        try:
            r = client.get(url, follow_redirects=True)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                last_err = f"HTTP {r.status_code}"
                _sleep_backoff(attempt)
                continue
            if r.status_code >= 400:
                return r.status_code, None, f"HTTP {r.status_code}"
            return r.status_code, r.content, None
        except httpx.HTTPError as e:
            last_err = str(e)
            if attempt < MAX_RETRIES - 1:
                _sleep_backoff(attempt)
                continue
            return None, None, last_err
    return None, None, last_err or "unknown error"


def run_scrape(
    allowlist_path: Path | None = None,
    output_dir: Path | None = None,
    snapshots_dir: Path | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> RunReport:
    allowlist_path = allowlist_path or DEFAULT_ALLOWLIST
    output_dir = output_dir or OUTPUT_DIR
    snapshots_dir = snapshots_dir or SNAPSHOTS_DIR

    started = datetime.now(timezone.utc)
    report = RunReport(
        started_at=started.isoformat(),
        finished_at="",
        allowlist=allowlist_path.resolve(),
        results=[],
    )

    urls = load_allowlist(allowlist_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}

    with httpx.Client(
        headers=headers,
        timeout=REQUEST_TIMEOUT_S,
        http2=False,
    ) as client:
        robots_gate = RobotsGate(client, user_agent)

        for i, url in enumerate(urls):
            slug = url_slug(url)
            fetched_at = datetime.now(timezone.utc).isoformat()

            if not robots_gate.allowed(url):
                report.results.append(
                    UrlResult(
                        url=url,
                        slug=slug,
                        ok=False,
                        status_code=None,
                        fetched_at=fetched_at,
                        error="disallowed by robots.txt",
                    )
                )
                logger.error("robots.txt disallows %s", url)
                continue

            status, body, err = fetch_url_with_retries(client, url)
            if body is None:
                report.results.append(
                    UrlResult(
                        url=url,
                        slug=slug,
                        ok=False,
                        status_code=status,
                        fetched_at=fetched_at,
                        error=err or "empty body",
                    )
                )
                logger.error("fetch failed %s: %s", url, err)
            else:
                digest = hashlib.sha256(body).hexdigest()
                meta = {
                    "url": url,
                    "slug": slug,
                    "status_code": status,
                    "fetched_at": fetched_at,
                    "content_sha256": digest,
                    "bytes": len(body),
                }
                page_dir = output_dir / slug
                page_dir.mkdir(parents=True, exist_ok=True)
                html_path = page_dir / "body.html"
                meta_path = page_dir / "meta.json"
                html_path.write_bytes(body)
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

                snap_dir = snapshots_dir / slug
                snap_dir.mkdir(parents=True, exist_ok=True)
                (snap_dir / "latest.html").write_bytes(body)
                (snap_dir / "latest.meta.json").write_text(
                    json.dumps(meta, indent=2), encoding="utf-8"
                )

                report.results.append(
                    UrlResult(
                        url=url,
                        slug=slug,
                        ok=True,
                        status_code=status,
                        fetched_at=fetched_at,
                        error=None,
                        content_sha256=digest,
                        bytes_written=len(body),
                    )
                )
                logger.info("ok %s -> %s", url, html_path)

            if i < len(urls) - 1 and DELAY_BETWEEN_URLS_S > 0:
                time.sleep(DELAY_BETWEEN_URLS_S)

    report.finished_at = datetime.now(timezone.utc).isoformat()
    summary_path = output_dir / "run-report.json"
    summary_path.write_text(
        json.dumps(report.to_json(), indent=2),
        encoding="utf-8",
    )
    return report


def exit_code_for_report(report: RunReport) -> int:
    failed = [r for r in report.results if not r.ok]
    if failed and STRICT:
        return 1
    return 0
