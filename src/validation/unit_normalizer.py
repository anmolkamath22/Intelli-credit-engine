"""Unit normalization to INR crores with confidence metadata."""

from __future__ import annotations

import re
from typing import Any


UNIT_MULTIPLIER_TO_CRORE = {
    "crore": 1.0,
    "crores": 1.0,
    "cr": 1.0,
    "million": 0.1,
    "mn": 0.1,
    "lakh": 0.01,
    "lakhs": 0.01,
    "thousand": 0.0001,
    "k": 0.0001,
    "rupees": 0.0000001,
    "rs": 0.0000001,
    "inr": 0.0000001,
}


def detect_unit_from_text(text: str) -> str:
    """Detect dominant financial unit mention in raw text."""
    t = (text or "").lower()
    hints = [
        (r"₹\s*in\s*crores?|inr\s*crores?|amount\s*in\s*crores?", "crore"),
        (r"₹\s*in\s*millions?|inr\s*millions?|amount\s*in\s*millions?", "million"),
        (r"₹\s*in\s*lakhs?|inr\s*lakhs?|amount\s*in\s*lakhs?", "lakh"),
        (r"₹\s*in\s*thousands?|inr\s*thousands?|amount\s*in\s*thousands?", "thousand"),
    ]
    for pattern, unit in hints:
        if re.search(pattern, t):
            return unit
    if "million" in t:
        return "million"
    if "lakh" in t:
        return "lakh"
    if "thousand" in t:
        return "thousand"
    return "crore"


def detect_unit_with_context(text: str) -> dict[str, Any]:
    """Detect unit with confidence and evidence context."""
    t = (text or "").lower()
    patterns = [
        (r"(?:₹|rs\.?|inr)\s*(?:in)?\s*crores?", "crore", 0.95),
        (r"(?:₹|rs\.?|inr)\s*(?:in)?\s*millions?", "million", 0.95),
        (r"(?:₹|rs\.?|inr)\s*(?:in)?\s*lakhs?", "lakh", 0.9),
        (r"(?:₹|rs\.?|inr)\s*(?:in)?\s*thousands?", "thousand", 0.9),
        (r"amounts?\s*(?:are)?\s*(?:in)?\s*crores?", "crore", 0.8),
        (r"amounts?\s*(?:are)?\s*(?:in)?\s*millions?", "million", 0.8),
    ]
    for pat, unit, conf in patterns:
        m = re.search(pat, t)
        if m:
            return {
                "unit": unit,
                "confidence": conf,
                "evidence": m.group(0),
                "uncertain": conf < 0.7,
            }
    # fallback heuristics
    if "million" in t:
        return {"unit": "million", "confidence": 0.55, "evidence": "keyword:million", "uncertain": True}
    if "lakh" in t:
        return {"unit": "lakh", "confidence": 0.55, "evidence": "keyword:lakh", "uncertain": True}
    if "thousand" in t:
        return {"unit": "thousand", "confidence": 0.55, "evidence": "keyword:thousand", "uncertain": True}
    return {"unit": "crore", "confidence": 0.45, "evidence": "default", "uncertain": True}


def normalize_to_crore(value: float | int | None, unit: str, uncertain: bool = False) -> float | None:
    """Convert numeric value from detected unit to INR crores."""
    if value is None:
        return None
    # If unit is uncertain, do not silently normalize, return as-is
    if uncertain:
        return float(value)
    factor = UNIT_MULTIPLIER_TO_CRORE.get((unit or "").strip().lower(), 1.0)
    return float(value) * factor
