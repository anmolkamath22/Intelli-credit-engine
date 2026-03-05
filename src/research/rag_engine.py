"""RAG wrapper over local vector retriever."""

from __future__ import annotations

from src.vector_store.retriever import VectorRetriever


def rag_query(retriever: VectorRetriever, query: str, top_k: int = 5) -> list[dict]:
    """Retrieve supporting evidence chunks for a query."""
    return retriever.query(query, top_k=top_k)
