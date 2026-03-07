"""RAG wrapper over local vector retriever."""

from __future__ import annotations

from src.vector_store.retriever import VectorRetriever


def rag_query(retriever: VectorRetriever, query: str, top_k: int = 5) -> list[dict]:
    """Retrieve supporting evidence chunks for a query."""
    return retriever.query(query, top_k=top_k)


def rag_query_section(
    retriever: VectorRetriever,
    query: str,
    top_k: int = 5,
    source_types: list[str] | None = None,
    section_type: str | None = None,
) -> list[dict]:
    """Section-aware retrieval with source-type filters."""
    return retriever.query(query, top_k=top_k, source_types=source_types, section_type=section_type)
