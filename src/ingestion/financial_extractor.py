"""Financial metric extraction from JSON/CSV/PDF text."""

from __future__ import annotations

import re
from typing import Any


AUDITOR_FLAGS = [
    "qualified opinion",
    "emphasis of matter",
    "material weakness",
    "going concern",
    "adverse opinion",
]


def _num_from_text(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except Exception:
        return None


def extract_financials_from_text(text: str) -> dict[str, Any]:
    """Extract primary financial metrics from raw document text."""
    lower = (text or "").lower()
    return {
        "revenue": _num_from_text(r"(?:revenue|total income)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "net_profit": _num_from_text(r"(?:net profit|pat|profit after tax)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "debt": _num_from_text(r"(?:total debt|borrowings|debt)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "total_assets": _num_from_text(r"(?:total assets)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "total_liabilities": _num_from_text(r"(?:total liabilities)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "cash_flow": _num_from_text(r"(?:cash flow from operations|cash flow)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "ebitda": _num_from_text(r"(?:ebitda|operating profit)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "working_capital": _num_from_text(r"(?:working capital)[^\d]{0,25}(\d[\d,]*\.?\d*)", text),
        "auditor_remarks": [f for f in AUDITOR_FLAGS if f in lower],
    }


def merge_financial_dicts(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge extracted financial dicts preferring first non-null values."""
    keys = [
        "revenue",
        "net_profit",
        "debt",
        "total_assets",
        "total_liabilities",
        "cash_flow",
        "ebitda",
        "working_capital",
    ]
    out: dict[str, Any] = {}
    for k in keys:
        out[k] = next((d.get(k) for d in items if d.get(k) is not None), None)

    remarks = []
    for d in items:
        for r in d.get("auditor_remarks", []) or []:
            if r not in remarks:
                remarks.append(r)
    out["auditor_remarks"] = remarks
    return out
