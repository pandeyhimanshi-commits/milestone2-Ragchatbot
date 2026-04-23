from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class EntitySlot:
    amc: str | None = None
    scheme_ids: list[str] = field(default_factory=list)
    last_doc_type: str | None = None


@dataclass
class ThreadContext:
    thread_id: str
    recent_messages: list[str] = field(default_factory=list)
    entity_slot: EntitySlot = field(default_factory=EntitySlot)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ThreadContextStore:
    def __init__(self, path: Path, history_limit: int) -> None:
        self.path = path
        self.history_limit = max(1, history_limit)

    def _read_all(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def get(self, thread_id: str) -> ThreadContext:
        rows = self._read_all()
        row = rows.get(thread_id) or {}
        entity_raw = row.get("entity_slot") or {}
        return ThreadContext(
            thread_id=thread_id,
            recent_messages=[
                str(x) for x in (row.get("recent_messages") or [])
            ][-self.history_limit :],
            entity_slot=EntitySlot(
                amc=(str(entity_raw.get("amc")) if entity_raw.get("amc") else None),
                scheme_ids=[str(x) for x in (entity_raw.get("scheme_ids") or [])],
                last_doc_type=(
                    str(entity_raw.get("last_doc_type")) if entity_raw.get("last_doc_type") else None
                ),
            ),
            updated_at=str(row.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )

    def put(self, ctx: ThreadContext) -> None:
        rows = self._read_all()
        ctx.updated_at = datetime.now(timezone.utc).isoformat()
        rows[ctx.thread_id] = {
            "recent_messages": ctx.recent_messages[-self.history_limit :],
            "entity_slot": {
                "amc": ctx.entity_slot.amc,
                "scheme_ids": ctx.entity_slot.scheme_ids,
                "last_doc_type": ctx.entity_slot.last_doc_type,
            },
            "updated_at": ctx.updated_at,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

