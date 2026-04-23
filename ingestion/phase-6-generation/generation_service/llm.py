from __future__ import annotations

import logging
import time
from typing import Any

from generation_service.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)
_client: Any | None = None
_client_mode: str | None = None


def _get_client() -> tuple[Any, str]:
    global _client
    global _client_mode
    if _client is not None and _client_mode is not None:
        return _client, _client_mode

    # Primary SDK: google-genai (import path: from google import genai)
    try:
        from google import genai  # type: ignore

        _client = genai.Client(api_key=GEMINI_API_KEY)
        _client_mode = "google_genai"
        return _client, _client_mode
    except Exception:
        pass

    # Fallback SDK: google-generativeai (import path: import google.generativeai as genai)
    try:
        import google.generativeai as legacy_genai  # type: ignore

        legacy_genai.configure(api_key=GEMINI_API_KEY)
        _client = legacy_genai
        _client_mode = "google_generativeai"
        return _client, _client_mode
    except Exception as exc:
        raise RuntimeError(
            "Gemini SDK import failed. Install `google-genai` or `google-generativeai`."
        ) from exc


def gemini_generate(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set for Phase 6 generation")
    client, mode = _get_client()
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            if mode == "google_genai":
                out = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                text = (out.text or "").strip()
            else:
                # google-generativeai fallback path
                model = client.GenerativeModel(GEMINI_MODEL)
                out = model.generate_content(prompt)
                text = (getattr(out, "text", None) or "").strip()
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
