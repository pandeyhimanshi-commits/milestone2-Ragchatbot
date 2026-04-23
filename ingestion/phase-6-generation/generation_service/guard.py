from __future__ import annotations

import re

ADVISORY_PATTERNS = [
    r"\bshould i\b",
    r"\bwhich (fund|one) (is|to) (better|best)\b",
    r"\bbetter fund\b",
    r"\bwhich one to pick\b",
    r"\bbest returns?\b",
    r"\bwill (it|this fund) go up\b",
    r"\bguarantee(d)? returns?\b",
    r"\bcompare\b",
]


def is_refusal_query(query: str) -> bool:
    q = query.strip().lower()
    return any(re.search(p, q) for p in ADVISORY_PATTERNS)

