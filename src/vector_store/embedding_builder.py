"""Deterministic embedding builder for local RAG."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


@dataclass
class EmbeddingBuilder:
    """Hash-based embedding generator for offline deterministic behavior."""

    dim: int = 64

    def embed(self, text: str) -> np.ndarray:
        """Embed text into fixed-length vector."""
        digest = hashlib.sha512((text or "").encode("utf-8")).digest()
        base = np.frombuffer(digest, dtype=np.uint8).astype("float32")
        vec = np.resize(base, self.dim)
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-8)
