from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LimitCheck:
    allowed: bool
    reason: str | None = None
    retry_after_s: int | None = None


class FixedWindowRateLimiter:
    def __init__(self, path: Path, window_s: int = 60) -> None:
        self.path = path
        self.window_s = window_s

    def _read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def check_and_consume(self, key: str, limit: int) -> LimitCheck:
        now = int(time.time())
        data = self._read()
        row = data.get(key) or {}
        window_start = int(row.get("window_start", now))
        used = int(row.get("used", 0))
        if now - window_start >= self.window_s:
            window_start = now
            used = 0

        if used >= limit:
            retry_after = max(1, self.window_s - (now - window_start))
            return LimitCheck(
                allowed=False,
                reason=f"rate_limited:{key}",
                retry_after_s=retry_after,
            )

        used += 1
        data[key] = {"window_start": window_start, "used": used}
        self._write(data)
        return LimitCheck(allowed=True)

