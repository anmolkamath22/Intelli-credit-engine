"""Research agent orchestrating local intelligence modules."""

from __future__ import annotations

import json
from pathlib import Path

from src.research.board_of_directors_extractor import extract_board_of_directors
from src.research.company_profile_builder import build_company_overview, build_company_profile
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
    evidence_output_path: Path | None = None,
    top_k: int = 5,
) -> dict:
    """Generate research summary using local signals + retrieved evidence."""
    profile = build_company_overview(financials, company_name)
    proc_dir = output_path.parent
    entity_profile = {}
    officer_inputs = {}
    try:
        entity_profile = json.loads((proc_dir / "entity_profile.json").read_text(encoding="utf-8"))
    except Exception:
        entity_profile = {}
    try:
        officer_inputs = json.loads((proc_dir / "officer_inputs.json").read_text(encoding="utf-8"))
    except Exception:
        officer_inputs = {}

    board = extract_board_of_directors(company_dir)
    legal = lookup_litigation(company_dir, company_name=company_name, board_members=board)
    news = analyze_news(company_dir, company_name=company_name, board_members=board)
    rating = _load_external_rating(company_dir)

    sector_risk = "moderate"
    sector_headwinds = []
    if news.get("risk_assessment", "").startswith("unknown"):
        sector_headwinds.append("Insufficient external news evidence")
    if news["news_sentiment_score"] < 40:
        sector_headwinds.append("Weak media sentiment")
    if legal.get("litigation_risk_status", "").startswith("unknown"):
        sector_headwinds.append("Insufficient public litigation evidence")
    if legal["litigation_risk_score"] > 60:
        sector_headwinds.append("Elevated legal disputes")

    if len(sector_headwinds) >= 2:
        sector_risk = "high"
    elif not sector_headwinds:
        sector_risk = "low"

    promoter_risk = min(100.0, legal["litigation_risk_score"] * 0.4 + (100 - news["news_sentiment_score"]) * 0.3)
    board_risk = round(min(100.0, promoter_risk * 0.6 + legal["litigation_risk_score"] * 0.3), 2)
    if news.get("risk_assessment", "").startswith("unknown") or legal.get("litigation_risk_status", "").startswith("unknown"):
        board_risk = min(100.0, board_risk + 8.0)

    financial_evidence = rag_query_section(
        retriever,
        "audited financial statement revenue ebitda net profit debt finance cost operating cash flow alm borrowing profile shareholding portfolio performance",
        top_k=max(3, top_k // 2),
        source_types=[
            "annual_reports",
            "financial_statements",
            "balance_sheets",
            "feature_summary",
            "alm",
            "shareholding_pattern",
            "borrowing_profile",
            "portfolio_cuts",
        ],
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
    structured_evidence = (news.get("evidence", []) + legal.get("evidence", []))[:60]

    # Deduplicate evidence by source/title/url.
    dedup = {}
    for ev in structured_evidence:
        key = (ev.get("source", ""), ev.get("title", ""), ev.get("url", ""))
        dedup[key] = ev
    structured_evidence = list(dedup.values())[:60]

    research_confidence = "high" if (news.get("confidence") == "high" and legal.get("litigation_confidence") == "high") else (
        "low" if (news.get("confidence") == "low" or legal.get("litigation_confidence") == "low") else "medium"
    )

    summary = {
        "company_overview": profile,
        "board_of_directors": board,
        "promoter_risk": round(float(promoter_risk), 2),
        "board_risk": board_risk,
        "litigation_count": legal["litigation_count"],
        "litigation_risk_score": legal["litigation_risk_score"],
        "litigation_confidence": legal.get("litigation_confidence", "low"),
        "litigation_risk_status": legal.get("litigation_risk_status", "unknown_insufficient_public_evidence"),
        "negative_news_count": news["negative_news_count"],
        "news_sentiment_score": news["news_sentiment_score"],
        "news_confidence": news.get("confidence", "low"),
        "news_risk_assessment": news.get("risk_assessment", "unknown_insufficient_data"),
        "evidence_found": bool(news.get("evidence_found") or legal.get("litigation_evidence_found")),
        "research_confidence": research_confidence,
        "reputation_risk": round(max(0.0, 100.0 - news["news_sentiment_score"]), 2),
        "regulatory_risk": round(min(100.0, legal["litigation_risk_score"] * 0.7 + news["controversy_mentions"] * 12), 2),
        "sector_risk": sector_risk,
        "sector_headwinds": sector_headwinds,
        "case_summary": legal["case_summary"],
        "external_credit_rating": rating.get("credit_rating"),
        "rating_history": rating.get("rating_history", []),
        "rating_rationale": rating.get("rating_rationale"),
        "downgrade_flag": rating.get("downgrade_flag"),
        "supporting_evidence": evidence,
    }

    board_risk_summary = {
        "company_name": company_name,
        "board_of_directors": board,
        "board_risk_score": board_risk,
        "board_risk_confidence": "medium" if board else "low",
        "board_findings": [
            f"{ev.get('entity_name')}: {ev.get('risk_tag')} ({ev.get('confidence')})"
            for ev in structured_evidence
            if str(ev.get("entity_type", "")).lower() in {"director", "board"}
        ][:20],
    }

    litigation_summary = {
        "company_name": company_name,
        "litigation_count": legal["litigation_count"],
        "litigation_risk_score": legal["litigation_risk_score"],
        "litigation_risk_status": legal.get("litigation_risk_status", "unknown_insufficient_public_evidence"),
        "litigation_confidence": legal.get("litigation_confidence", "low"),
        "insolvency_flag": legal.get("insolvency_flag", 0),
    }

    promoter_summary = (
        f"Promoter/board risk score {round(float(promoter_risk), 2)}/100 with board risk {board_risk}/100. "
        f"External evidence confidence: news={news.get('confidence', 'low')}, litigation={legal.get('litigation_confidence', 'low')}."
    )
    company_profile = build_company_profile(
        company_name=company_name,
        entity_profile=entity_profile,
        financials=financials,
        board_of_directors=board,
        promoter_summary=promoter_summary,
        research_summary=summary,
        litigation_summary=litigation_summary,
        officer_inputs=officer_inputs,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    if evidence_output_path:
        evidence_output_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_output_path.write_text(json.dumps(structured_evidence, indent=2, ensure_ascii=True), encoding="utf-8")
    (proc_dir / "litigation_summary.json").write_text(json.dumps(litigation_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    (proc_dir / "litigation_evidence.json").write_text(
        json.dumps([ev for ev in structured_evidence if ev.get("risk_tag") in {"litigation_risk", "regulatory_risk"}], indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (proc_dir / "board_risk_summary.json").write_text(json.dumps(board_risk_summary, indent=2, ensure_ascii=True), encoding="utf-8")
    (proc_dir / "company_profile.json").write_text(json.dumps(company_profile, indent=2, ensure_ascii=True), encoding="utf-8")
    return summary
