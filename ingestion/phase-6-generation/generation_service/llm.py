from __future__ import annotations

import logging
import time

from google import genai

from generation_service.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def gemini_generate(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set for Phase 6 generation")
    client = _get_client()
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            out = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = (out.text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned empty text")
            return text
        except Exception as exc:
            last_exc = exc
            if attempt == 2:
                break
            backoff_s = 1.5 * (attempt + 1)
            logger.warning(
                "gemini request failed (attempt=%s): %s; retrying in %.1fs",
                attempt + 1,
                type(exc).__name__,
                backoff_s,
            )
            time.sleep(backoff_s)
    assert last_exc is not None
    raise last_exc
