from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ThreadState:
    thread_id: str
    history: list[str] = field(default_factory=list)
    scheme_slug: str | None = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ThreadStore:
    def __init__(self, path: Path, history_limit: int) -> None:
        self.path = path
        self.history_limit = max(1, history_limit)

    def _read_all(self) -> dict[str, dict]:
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def get(self, thread_id: str) -> ThreadState:
        rows = self._read_all()
        row = rows.get(thread_id) or {}
        history = [str(x) for x in (row.get("history") or [])][-self.history_limit :]
        return ThreadState(
            thread_id=thread_id,
            history=history,
            scheme_slug=(str(row.get("scheme_slug")) if row.get("scheme_slug") else None),
            updated_at=str(row.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )

    def put(self, state: ThreadState) -> None:
        rows = self._read_all()
        state.updated_at = datetime.now(timezone.utc).isoformat()
        rows[state.thread_id] = {
            "history": state.history[-self.history_limit :],
            "scheme_slug": state.scheme_slug,
            "updated_at": state.updated_at,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

