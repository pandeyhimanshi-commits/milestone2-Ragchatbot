from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from threading_service.concurrency import PerThreadSemaphorePool
from threading_service.config import (
    ALLOWLIST_PATH,
    MAX_PARALLEL_PER_THREAD,
    OUTPUT_DIR,
    PHASE6_ROOT,
    RATE_LIMIT_PER_IP_PER_MIN,
    RATE_LIMIT_PER_THREAD_PER_MIN,
    RATE_LIMIT_STATE_PATH,
    THREAD_HISTORY_LIMIT,
    THREAD_STATE_PATH,
)
from threading_service.limiters import FixedWindowRateLimiter
from threading_service.state import ThreadContextStore

sys.path.insert(0, str(PHASE6_ROOT))
from generation_service.runner import run_generation  # type: ignore  # noqa: E402

logger = logging.getLogger(__name__)
_SEM_POOL = PerThreadSemaphorePool(max_parallel_per_thread=MAX_PARALLEL_PER_THREAD)


@dataclass
class ChatTurnResult:
    thread_id: str
    decision: str
    answer: str
    citation_url: str | None
    generation: dict[str, Any]
    state: dict[str, Any]
    started_at: str
    finished_at: str
    message_hash: str

    def to_json(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "decision": self.decision,
            "answer": self.answer,
            "citation_url": self.citation_url,
            "generation": self.generation,
            "state": self.state,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "message_hash": self.message_hash,
        }


def _allowlist_slugs() -> list[str]:
    if not ALLOWLIST_PATH.is_file():
        return []
    slugs: list[str] = []
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if t.startswith("- http://") or t.startswith("- https://"):
            url = t[2:].strip().rstrip("/")
            slugs.append(url.split("/")[-1])
    return slugs


def _extract_scheme_ids(message: str, slugs: list[str]) -> list[str]:
    q = message.lower()
    out: list[str] = []
    generic_tokens = {
        "hdfc",
        "fund",
        "direct",
        "growth",
        "plan",
        "mutual",
    }
    for s in slugs:
        hint = s.replace("-", " ")
        tokens = [t for t in hint.split() if len(t) > 3 and t not in generic_tokens]
        # Require at least one specific token match (e.g., "mid", "elss", "equity").
        if tokens and any(token in q for token in tokens):
            out.append(s)
    return sorted(set(out))


def _extract_amc(message: str) -> str | None:
    q = message.lower()
    if "hdfc" in q:
        return "HDFC"
    return None


def run_chat_turn(thread_id: str, user_message: str, client_ip: str = "127.0.0.1") -> ChatTurnResult:
    started = datetime.now(timezone.utc).isoformat()
    msg_hash = hashlib.sha256(user_message.encode("utf-8")).hexdigest()

    limiter = FixedWindowRateLimiter(path=RATE_LIMIT_STATE_PATH)
    thread_limit = limiter.check_and_consume(f"thread:{thread_id}", RATE_LIMIT_PER_THREAD_PER_MIN)
    if not thread_limit.allowed:
        raise RuntimeError(f"thread rate limit exceeded; retry_after={thread_limit.retry_after_s}s")
    ip_limit = limiter.check_and_consume(f"ip:{client_ip}", RATE_LIMIT_PER_IP_PER_MIN)
    if not ip_limit.allowed:
        raise RuntimeError(f"ip rate limit exceeded; retry_after={ip_limit.retry_after_s}s")

    with _SEM_POOL.acquire(thread_id=thread_id, timeout_s=8.0) as locked:
        if not locked:
            raise RuntimeError("thread busy: concurrent request limit reached")

        store = ThreadContextStore(path=THREAD_STATE_PATH, history_limit=THREAD_HISTORY_LIMIT)
        ctx = store.get(thread_id)
        ctx.recent_messages.append(user_message.strip())
        ctx.recent_messages = ctx.recent_messages[-THREAD_HISTORY_LIMIT:]

        slugs = _allowlist_slugs()
        scheme_ids = _extract_scheme_ids(user_message, slugs)
        if scheme_ids:
            ctx.entity_slot.scheme_ids = scheme_ids
        amc = _extract_amc(user_message)
        if amc:
            ctx.entity_slot.amc = amc

        gen = run_generation(query=user_message, thread_id=thread_id)
        gen_json = gen.to_json()
        # Maintain last retrieved doc type for thread context.
        grounded = (
            (gen_json.get("retrieval") or {}).get("grounded")
            or (gen_json.get("retrieval") or {}).get("retrieved")
            or []
        )
        if grounded:
            md = grounded[0].get("metadata") or {}
            if md.get("doc_type"):
                ctx.entity_slot.last_doc_type = str(md["doc_type"])
            if md.get("slug"):
                slug = str(md["slug"])
                if slug not in ctx.entity_slot.scheme_ids:
                    ctx.entity_slot.scheme_ids.append(slug)

        store.put(ctx)

    finished = datetime.now(timezone.utc).isoformat()
    result = ChatTurnResult(
        thread_id=thread_id,
        decision=str(gen_json.get("decision") or ""),
        answer=str(gen_json.get("answer") or ""),
        citation_url=(str(gen_json.get("citation_url")) if gen_json.get("citation_url") else None),
        generation=gen_json,
        state={
            "recent_messages_count": len(ctx.recent_messages),
            "entity_slot": {
                "amc": ctx.entity_slot.amc,
                "scheme_ids": ctx.entity_slot.scheme_ids,
                "last_doc_type": ctx.entity_slot.last_doc_type,
            },
        },
        started_at=started,
        finished_at=finished,
        message_hash=msg_hash,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "threading-last.json").write_text(
        json.dumps(result.to_json(), indent=2),
        encoding="utf-8",
    )
    logger.info("chat turn complete thread_id=%s decision=%s", thread_id, result.decision)
    return result

