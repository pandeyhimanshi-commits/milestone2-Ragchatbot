from __future__ import annotations

import json
import re
from typing import Any

def _parse_next_data(html: bytes | str) -> dict[str, Any] | None:
    raw = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else html
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(v: Any) -> int | None:
    f = _to_float(v)
    if f is None:
        return None
    return int(f)


def scheme_name_from_url_slug(slug: str) -> str:
    """
    Human label aligned with the allowlist URL last segment, not whatever Groww puts in
    mfServerSideData.scheme_name (which can disagree or be stale for the same path).
    """
    acronyms = {"hdfc": "HDFC", "elss": "ELSS"}
    parts: list[str] = []
    for w in (slug or "").split("-"):
        if not w:
            continue
        low = w.lower()
        if low in acronyms:
            parts.append(acronyms[low])
        else:
            parts.append(w[:1].upper() + w[1:].lower())
    return " ".join(parts) if parts else (slug or "This fund")


def extract_metrics(html: bytes | str) -> tuple[dict[str, Any] | None, list[str]]:
    """
    Parse Groww mutual-fund page HTML; return metrics dict and list of error/warning strings.
    """
    errors: list[str] = []
    data = _parse_next_data(html)
    if not data:
        return None, ["missing or invalid __NEXT_DATA__"]

    mf = data.get("props", {}).get("pageProps", {}).get("mfServerSideData")
    if not isinstance(mf, dict):
        return None, ["missing mfServerSideData in pageProps"]

    nav = _to_float(mf.get("nav"))
    min_sip = _to_int(mf.get("min_sip_investment"))
    aum = _to_float(mf.get("aum"))
    expense = _to_float(mf.get("expense_ratio"))
    rating = mf.get("groww_rating")
    if rating is not None and not isinstance(rating, int):
        ri = _to_int(rating)
        rating = ri

    groww_label = (mf.get("scheme_name") or mf.get("fund_name") or "")
    nav_date = mf.get("nav_date")

    metrics: dict[str, Any] = {
        "nav": {
            "value": nav,
            "currency": "INR",
            "unit": "per unit",
            "as_of": nav_date,
        },
        "minimum_sip": {
            "value": min_sip,
            "currency": "INR",
            "description": "Minimum SIP instalment amount",
        },
        "fund_size": {
            "value": aum,
            "unit": "INR Cr",
            "description": "Assets under management (AUM) as shown on Groww",
        },
        "expense_ratio": {
            "value": expense,
            "unit": "% p.a.",
            "description": "Total expense ratio (TER)",
        },
        "rating": {
            "groww_rating": rating,
            "scale_max": 10,
            "description": "Groww risk-reward style rating (when present)",
        },
    }

    if nav is None:
        errors.append("nav missing or invalid")
    if min_sip is None:
        errors.append("min_sip_investment missing or invalid")
    if aum is None:
        errors.append("aum missing or invalid")
    if expense is None:
        errors.append("expense_ratio missing or invalid")

    return (
        {
            "scheme_name": groww_label,
            "metrics": metrics,
        },
        errors,
    )


def build_retrieval_text(scheme_name: str | None, metrics: dict[str, Any]) -> str:
    """Single plain passage for downstream chunking / embedding."""
    lines: list[str] = []
    if scheme_name:
        lines.append(f"Scheme: {scheme_name}.")
    nav = metrics.get("nav") or {}
    if nav.get("value") is not None:
        ao = nav.get("as_of")
        lines.append(
            f"NAV ₹{nav['value']} per unit"
            + (f" as of {ao}" if ao else "")
            + "."
        )
    ms = metrics.get("minimum_sip") or {}
    if ms.get("value") is not None:
        lines.append(f"Minimum SIP ₹{ms['value']}.")
    fs = metrics.get("fund_size") or {}
    if fs.get("value") is not None:
        lines.append(f"Fund size (AUM) ₹{fs['value']} Cr.")
    er = metrics.get("expense_ratio") or {}
    if er.get("value") is not None:
        lines.append(f"Expense ratio {er['value']}% p.a.")
    rt = metrics.get("rating") or {}
    gr = rt.get("groww_rating")
    if gr is not None:
        lines.append(f"Groww rating {gr}/10.")
    return " ".join(lines)
