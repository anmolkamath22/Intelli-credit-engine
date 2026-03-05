"""In-memory vector retriever for semantic evidence lookup."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.vector_store.embedding_builder import EmbeddingBuilder


@dataclass
class VectorRecord:
    """Vectorized chunk record."""

    source: str
    chunk: str
    vector: np.ndarray


class VectorRetriever:
    """Stores vectors and retrieves top-k similar chunks."""

    def __init__(self, embedder: EmbeddingBuilder) -> None:
        self.embedder = embedder
        self.records: list[VectorRecord] = []

    def add(self, source: str, chunk: str) -> None:
        """Add chunk to vector index."""
        self.records.append(VectorRecord(source=source, chunk=chunk, vector=self.embedder.embed(chunk)))

    def query(self, text: str, top_k: int = 5) -> list[dict]:
        """Retrieve top-k semantically similar chunks."""
        if not self.records:
            return []
        q = self.embedder.embed(text)
        sims = [(float(np.dot(q, r.vector)), r) for r in self.records]
        sims.sort(key=lambda x: x[0], reverse=True)
        return [
            {"score": s, "source": r.source, "chunk": r.chunk}
            for s, r in sims[:top_k]
        ]
