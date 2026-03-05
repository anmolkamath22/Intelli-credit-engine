"""Text processing helpers."""

from __future__ import annotations

import re


def slugify(value: str) -> str:
    """Convert text to filesystem-safe slug."""
    out = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower())
    return re.sub(r"_+", "_", out).strip("_") or "company"


def clean_text(text: str) -> str:
    """Normalize whitespace for model processing."""
    text = re.sub(r"[\r\n\t]+", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def split_words(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks by words."""
    words = clean_text(text).split()
    if not words:
        return []
    step = max(chunk_size - overlap, 1)
    out = []
    i = 0
    while i < len(words):
        out.append(" ".join(words[i : i + chunk_size]))
        i += step
    return out
