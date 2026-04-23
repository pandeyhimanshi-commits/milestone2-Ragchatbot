from __future__ import annotations

import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import Iterator


class PerThreadSemaphorePool:
    def __init__(self, max_parallel_per_thread: int) -> None:
        self.max_parallel_per_thread = max(1, max_parallel_per_thread)
        self._pool: dict[str, threading.BoundedSemaphore] = defaultdict(
            lambda: threading.BoundedSemaphore(self.max_parallel_per_thread)
        )

    @contextmanager
    def acquire(self, thread_id: str, timeout_s: float = 5.0) -> Iterator[bool]:
        sem = self._pool[thread_id]
        ok = sem.acquire(timeout=timeout_s)
        try:
            yield ok
        finally:
            if ok:
                sem.release()

