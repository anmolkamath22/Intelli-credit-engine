"""Research agent orchestrating local intelligence modules."""

from __future__ import annotations

import json
from pathlib import Path

from src.research.company_profile_builder import build_company_overview
from src.research.litigation_lookup import lookup_litigation
from src.research.news_crawler import analyze_news
from src.research.rag_engine import rag_query_section
from src.vector_store.retriever import VectorRetriever


def _load_external_rating(company_dir: Path) -> dict:
    """Load optional external credit rating if available in local dataset."""
    candidates = [
        company_dir / "ratings" / "credit_rating.json",
        company_dir / "credit_rating.json",
    ]
    for c in candidates:
        if c.exists():
            try:
                payload = json.loads(c.read_text(encoding="utf-8"))
                return {
                    "credit_rating": payload.get("credit_rating"),
                    "rating_history": payload.get("rating_history", []),
                    "rating_rationale": payload.get("rating_rationale"),
                    "downgrade_flag": payload.get("downgrade_flag"),
                }
            except Exception:
                continue
    return {}


def run_research_agent(
    company_name: str,
    financials: dict,
    company_dir: Path,
    retriever: VectorRetriever,
    output_path: Path,
    top_k: int = 5,
) -> dict:
    """Generate research summary using local signals + retrieved evidence."""
    profile = build_company_overview(financials, company_name)
    legal = lookup_litigation(company_dir)
    news = analyze_news(company_dir)
    rating = _load_external_rating(company_dir)

    sector_risk = "moderate"
    sector_headwinds = []
    if news["news_sentiment_score"] < 40:
        sector_headwinds.append("Weak media sentiment")
    if legal["litigation_risk_score"] > 60:
        sector_headwinds.append("Elevated legal disputes")

    if len(sector_headwinds) >= 2:
        sector_risk = "high"
    elif not sector_headwinds:
        sector_risk = "low"

    promoter_risk = min(100.0, legal["litigation_risk_score"] * 0.4 + (100 - news["news_sentiment_score"]) * 0.3)

    financial_evidence = rag_query_section(
        retriever,
        "audited financial statement revenue ebitda net profit debt finance cost operating cash flow",
        top_k=max(3, top_k // 2),
        source_types=["annual_reports", "financial_statements", "balance_sheets", "feature_summary"],
        section_type="financial",
    )
    legal_evidence = rag_query_section(
        retriever,
        "litigation legal dispute insolvency nclt order tribunal case",
        top_k=max(3, top_k // 2),
        source_types=["legal_documents", "research_summary"],
        section_type="litigation",
    )
    sector_evidence = rag_query_section(
        retriever,
        "sector risk headwind demand slowdown commodity policy",
        top_k=top_k,
        source_types=["news_documents", "research_summary", "annual_reports"],
        section_type="industry",
    )
    evidence = (financial_evidence + legal_evidence + sector_evidence)[: max(top_k, 8)]

    summary = {
        "company_overview": profile,
        "promoter_risk": round(float(promoter_risk), 2),
        "litigation_count": legal["litigation_count"],
        "litigation_risk_score": legal["litigation_risk_score"],
        "negative_news_count": news["negative_news_count"],
        "news_sentiment_score": news["news_sentiment_score"],
        "sector_risk": sector_risk,
        "sector_headwinds": sector_headwinds,
        "case_summary": legal["case_summary"],
        "external_credit_rating": rating.get("credit_rating"),
        "rating_history": rating.get("rating_history", []),
        "rating_rationale": rating.get("rating_rationale"),
        "downgrade_flag": rating.get("downgrade_flag"),
        "supporting_evidence": evidence,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    return summary
