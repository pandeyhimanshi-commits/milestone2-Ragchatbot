from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from runtime_api.config import SECURITY_LOG_PATH

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b")
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
ACCOUNT_RE = re.compile(r"\b\d{9,18}\b")
OTP_RE = re.compile(r"\botp\b", re.IGNORECASE)

HARMFUL_PATTERNS = [
    r"\bbomb\b",
    r"\bexplosive\b",
    r"\bkill\b",
    r"\battack\b",
    r"\bfraud\b",
    r"\bscam\b",
    r"\bsteal\b",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"system prompt",
    r"developer message",
    r"reveal hidden rules",
    r"bypass guardrail",
]


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contains_pii(text: str) -> bool:
    return any(
        [
            EMAIL_RE.search(text),
            PHONE_RE.search(text),
            AADHAAR_RE.search(text),
            PAN_RE.search(text),
            ACCOUNT_RE.search(text),
            OTP_RE.search(text),
        ]
    )


def redact_text(text: str) -> str:
    out = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    out = PHONE_RE.sub("[REDACTED_PHONE]", out)
    out = AADHAAR_RE.sub("[REDACTED_AADHAAR]", out)
    out = PAN_RE.sub("[REDACTED_PAN]", out)
    out = ACCOUNT_RE.sub("[REDACTED_ACCOUNT]", out)
    return out


def is_harmful(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in HARMFUL_PATTERNS)


def has_prompt_injection_markers(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in PROMPT_INJECTION_PATTERNS)


def append_security_log(event: dict) -> None:
    SECURITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with SECURITY_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")

