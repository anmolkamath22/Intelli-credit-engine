"""Conversational CAM explainer agent using local RAG retrieval."""

from __future__ import annotations

import json
from pathlib import Path

from src.utils.text_processing import split_words
from src.vector_store.embedding_builder import EmbeddingBuilder
from src.vector_store.retriever import VectorRetriever


class CAMExplainerAgent:
    """Answers CAM questions with retrieved evidence snippets."""

    def __init__(self, company_processed_dir: Path) -> None:
        self.company_processed_dir = company_processed_dir
        self.retriever = VectorRetriever(EmbeddingBuilder(dim=64))
        self._build_index()

    def _build_index(self) -> None:
        docs = []
        for name in [
            "company_financials.json",
            "financial_features.json",
            "synthetic_gst_features.json",
            "synthetic_bank_features.json",
            "research_summary.json",
            "credit_features.json",
            "decision_trace.json",
            "scoring_output.json",
        ]:
            p = self.company_processed_dir / name
            if p.exists():
                try:
                    docs.append((name, p.read_text(encoding="utf-8", errors="ignore")))
                except Exception:
                    continue

        for src, text in docs:
            for chunk in split_words(text, chunk_size=180, overlap=30):
                self.retriever.add(source=src, chunk=chunk)

    def answer(self, question: str, top_k: int = 4) -> dict:
        """Answer question with evidence from indexed CAM/feature artifacts."""
        hits = self.retriever.query(question, top_k=top_k)
        if not hits:
            return {"answer": "No supporting evidence found in processed CAM artifacts.", "evidence": []}

        answer = (
            "Based on retrieved CAM artifacts, the recommendation depends on leverage, "
            "cashflow stability, litigation/news risk, management inputs, and detected risk flags."
        )
        return {"answer": answer, "evidence": hits}
