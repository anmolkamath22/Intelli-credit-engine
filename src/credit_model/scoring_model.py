"""Transparent credit scoring model."""

from __future__ import annotations


def score_credit(features: dict, financials: dict, scoring_cfg: dict, research: dict) -> dict:
    """Compute credit_score, recommended_loan_limit, and risk_premium."""
    financial_strength = max(0.0, 100 - min(features.get("debt_to_equity", 0) * 30, 80))
    profitability = max(0.0, min(features.get("profit_margin", 0) * 400, 100))
    cash_stability = max(0.0, min(features.get("cashflow_stability", 0) * 100, 100))
    trend_support = max(0.0, min(100.0, 50 + features.get("revenue_cagr_5y", 0) * 120 + features.get("debt_reduction_rate", 0) * 80))

    litigation_penalty = min(50.0, features.get("litigation_risk_score", 0) * 0.5)
    sentiment_bonus = (features.get("news_sentiment_score", 50) - 50) * 0.3
    management_penalty = min(40.0, features.get("management_risk_score", 0) * 0.4)
    gst_bonus = (features.get("gst_compliance_score", 50) - 50) * 0.15
    sector_penalty = min(20.0, features.get("sector_risk_score", 50.0) * 0.15)

    circular_penalty = 0.0
    if features.get("circular_trading_flag", 0):
        circular_penalty += 12.0
    if features.get("revenue_inflation_flag", 0):
        circular_penalty += 10.0

    base = (
        0.28 * financial_strength
        + 0.20 * profitability
        + 0.14 * cash_stability
        + 0.16 * max(0.0, 100 - management_penalty)
        + 0.12 * trend_support
    )
    adjusted = base - litigation_penalty - circular_penalty - sector_penalty + sentiment_bonus + gst_bonus
    credit_score = max(0.0, min(100.0, adjusted))

    # All values are assumed in INR crores.
    revenue = float(financials.get("revenue") or 0.0)
    ebitda = float(financials.get("ebitda") or 0.0)
    cap_by_revenue = 0.25 * revenue
    cap_by_ebitda = 4.0 * ebitda
    raw_limit = min(cap_by_revenue, cap_by_ebitda)
    recommended_loan_limit = round(max(0.0, raw_limit * (credit_score / 100.0)), 2)

    base_rate = float(scoring_cfg.get("base_rate", 9.5))
    max_risk_premium = float(scoring_cfg.get("max_risk_premium", 5.0))
    volatility_penalty = min(1.5, max(0.0, 1.2 - features.get("cashflow_stability", 1.0)))
    risk_premium = round(max(0.5, max_risk_premium * (1 - credit_score / 100.0) + volatility_penalty), 2)
    recommended_interest_rate = round(base_rate + risk_premium, 2)

    return {
        "credit_score": round(credit_score, 2),
        "loan_limit_cap_revenue_25pct": round(cap_by_revenue, 2),
        "loan_limit_cap_ebitda_4x": round(cap_by_ebitda, 2),
        "recommended_loan_limit": recommended_loan_limit,
        "risk_premium": risk_premium,
        "base_rate": round(base_rate, 2),
        "recommended_interest_rate": recommended_interest_rate,
    }
