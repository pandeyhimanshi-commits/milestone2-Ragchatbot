from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


def fetch_robots_txt(client: httpx.Client, origin: str) -> str | None:
    robots_url = urljoin(origin, "/robots.txt")
    try:
        r = client.get(robots_url, follow_redirects=True)
        if r.status_code == 200:
            return r.text
        logger.warning("robots.txt HTTP %s for %s", r.status_code, robots_url)
    except httpx.HTTPError as e:
        logger.warning("Could not fetch robots.txt %s: %s", robots_url, e)
    return None


def build_parser(origin: str, robots_body: str | None) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(urljoin(origin, "/robots.txt"))
    if robots_body:
        rp.parse(robots_body.splitlines())
    else:
        # No robots file: be conservative and still allow fetch of public scheme pages
        # (empty parse = no rules; can_fetch may default True in CPython)
        rp.parse([])
    return rp


def origin_of(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


class RobotsGate:
    """Respect robots.txt per host (architecture §4.2)."""

    def __init__(self, client: httpx.Client, user_agent: str) -> None:
        self._client = client
        self._user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        origin = origin_of(url)
        if origin not in self._cache:
            body = fetch_robots_txt(self._client, origin)
            self._cache[origin] = build_parser(origin, body)
        rp = self._cache[origin]
        try:
            return rp.can_fetch(self._user_agent, url)
        except Exception:
            logger.exception("robots can_fetch failed for %s", url)
            return False
