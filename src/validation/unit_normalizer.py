"""Unit normalization to INR crores."""

from __future__ import annotations

import re


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


def normalize_to_crore(value: float | int | None, unit: str) -> float | None:
    """Convert numeric value from detected unit to INR crores."""
    if value is None:
        return None
    factor = UNIT_MULTIPLIER_TO_CRORE.get((unit or "").strip().lower(), 1.0)
    return float(value) * factor

