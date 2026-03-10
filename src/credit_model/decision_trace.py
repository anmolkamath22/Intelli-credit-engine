"""Decision trace generation for explainable CAM outputs."""

from __future__ import annotations


def build_decision_trace(features: dict, scoring: dict, evidence: list[dict], research: dict, entity_profile: dict | None = None) -> dict:
    """Build explainability artifact with supportability + pricing decision context."""
    entity_profile = entity_profile or {}
    contributions = {
        "debt_to_equity": -min(25.0, features.get("debt_to_equity", 0) * 10),
        "profit_margin": min(20.0, features.get("profit_margin", 0) * 100),
        "revenue_cagr_5y": min(15.0, max(-15.0, features.get("revenue_cagr_5y", 0) * 120)),
        "cashflow_stability": min(20.0, features.get("cashflow_stability", 0) * 20),
        "litigation_risk_score": -min(25.0, features.get("litigation_risk_score", 0) * 0.3),
        "news_sentiment_score": (features.get("news_sentiment_score", 50) - 50) * 0.2,
        "management_risk_score": -min(20.0, features.get("management_risk_score", 0) * 0.2),
        "sector_risk_score": -min(16.0, features.get("sector_risk_score", 50) * 0.15),
        "circular_trading_flag": -10.0 if features.get("circular_trading_flag", 0) else 0.0,
        "revenue_inflation_flag": -8.0 if features.get("revenue_inflation_flag", 0) else 0.0,
    }

    risk_flags = []
    if features.get("litigation_risk_score", 0) >= 50:
        risk_flags.append("High litigation exposure")
    if features.get("news_sentiment_score", 50) < 40:
        risk_flags.append("Adverse media sentiment")
    if features.get("debt_to_equity", 0) > 1.5:
        risk_flags.append("High leverage")
    if features.get("cashflow_stability", 0) < 0.4:
        risk_flags.append("Unstable cash flow pattern")
    if features.get("revenue_cagr_5y", 0) < -0.1:
        risk_flags.append("Sharp negative revenue growth trend")
    if features.get("circular_trading_flag", 0):
        risk_flags.append("Potential circular trading behavior")
    if features.get("revenue_inflation_flag", 0):
        risk_flags.append("Potential revenue inflation risk")

    summary = (
        f"Credit score {scoring['credit_score']}. "
        f"Decision status: {scoring.get('decision_status', 'unknown')}. "
        f"Requested amount supportability: {scoring.get('requested_amount_supportability', 'unknown')}. "
        f"Interest decision: {scoring.get('interest_decision', 'unknown')}. "
        f"Decision weighted by financial strength, legal/news risk, management quality, circular-trading checks, and external-evidence confidence."
    )

    return {
        "feature_contribution": contributions,
        "risk_flags": risk_flags,
        "requested_loan_context": {
            "loan_type": scoring.get("loan_type") or entity_profile.get("loan_type"),
            "tenure_months": scoring.get("loan_tenure_months") or entity_profile.get("loan_tenure_months"),
            "requested_loan_amount": scoring.get("requested_loan_amount"),
            "requested_interest_rate": scoring.get("requested_interest_rate"),
            "supportability_cap": scoring.get("supportability_cap"),
            "requested_amount_supportability": scoring.get("requested_amount_supportability"),
        },
        "pricing_decision": {
            "interest_decision": scoring.get("interest_decision"),
            "recommended_interest_rate": scoring.get("recommended_interest_rate"),
            "key_conditions": scoring.get("key_conditions", []),
            "approval_rationale": scoring.get("approval_rationale", ""),
        },
        "confidence": {
            "research_confidence": research.get("research_confidence", "low"),
            "litigation_confidence": research.get("litigation_confidence", "low"),
            "news_confidence": research.get("news_confidence", "low"),
        },
        "supporting_evidence": evidence[:8],
        "research_context": {
            "promoter_risk": research.get("promoter_risk"),
            "sector_headwinds": research.get("sector_headwinds", []),
        },
        "reasoning_summary": summary,
    }
