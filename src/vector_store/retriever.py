"""In-memory vector retriever for semantic evidence lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from src.vector_store.embedding_builder import EmbeddingBuilder


@dataclass
class VectorRecord:
    """Vectorized chunk record."""

    source: str
    chunk: str
    vector: np.ndarray
    metadata: dict[str, Any]


class VectorRetriever:
    """Stores vectors and retrieves top-k similar chunks."""

    def __init__(self, embedder: EmbeddingBuilder) -> None:
        self.embedder = embedder
        self.records: list[VectorRecord] = []

    def add(self, source: str, chunk: str, metadata: dict[str, Any] | None = None) -> None:
        """Add chunk to vector index."""
        self.records.append(
            VectorRecord(source=source, chunk=chunk, vector=self.embedder.embed(chunk), metadata=metadata or {})
        )

    def query(
        self,
        text: str,
        top_k: int = 5,
        source_types: list[str] | None = None,
        section_type: str | None = None,
    ) -> list[dict]:
        """Retrieve top-k semantically similar chunks with strict targeting."""
        if not self.records:
            return []
        q = self.embedder.embed(text)
        sims = []
        for r in self.records:
            st = str(r.metadata.get("source_type", ""))
            sec = str(r.metadata.get("section_type", "general"))
            
            # Strict source_type filtering
            if source_types and st and st not in set(source_types):
                continue
                
            # Exclude completely unrelated sections (e.g. don't show litigation in financial)
            if section_type and sec != "general" and sec != section_type:
                # Still allow if it's the exact section requested
                continue
                
            score = float(np.dot(q, r.vector))
            # Heavy boost for exact section metadata match
            if section_type and sec == section_type:
                score += 0.30
                
            sims.append((score, r))
            
        sims.sort(key=lambda x: x[0], reverse=True)
        return [
            {"score": s, "source": r.source, "chunk": r.chunk, "metadata": r.metadata}
            for s, r in sims[:top_k]
        ]
