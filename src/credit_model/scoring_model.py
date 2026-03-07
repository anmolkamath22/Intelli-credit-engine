"""Transparent credit scoring model."""

from __future__ import annotations


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def score_credit(features: dict, financials: dict, scoring_cfg: dict, research: dict) -> dict:
    """Compute calibrated credit score and lending recommendation."""
    # Positive normalized factors (0..100)
    leverage = _clip(100.0 - float(features.get("debt_to_equity", 0.0)) * 35.0, 20.0, 100.0)
    profitability = _clip(50.0 + float(features.get("profit_margin", 0.0)) * 220.0, 0.0, 100.0)
    cash_stability = _clip(float(features.get("cashflow_stability", 0.0)) * 100.0, 0.0, 100.0)
    growth = _clip(50.0 + float(features.get("revenue_cagr_5y", 0.0)) * 160.0, 0.0, 100.0)
    coverage = _clip(float(features.get("interest_coverage", 0.0)) * 12.0, 0.0, 100.0)
    governance = _clip(100.0 - float(features.get("management_risk_score", 0.0)), 0.0, 100.0)

    positive_components = {
        "leverage": 0.20 * leverage,
        "profitability": 0.18 * profitability,
        "cash_stability": 0.18 * cash_stability,
        "growth": 0.14 * growth,
        "coverage": 0.12 * coverage,
        "governance": 0.10 * governance,
        "sentiment": 0.08 * _clip(float(features.get("news_sentiment_score", 50.0)), 0.0, 100.0),
    }
    positive_score = sum(positive_components.values())

    # Calibrated penalty block (capped so one feature cannot zero out the score)
    litigation_penalty = _clip(float(features.get("litigation_risk_score", 0.0)) * 0.16, 0.0, 14.0)
    sector_penalty = _clip(float(features.get("sector_risk_score", 50.0)) * 0.09, 2.0, 9.0)
    circular_penalty = 0.0
    circular_penalty += 6.0 if int(features.get("circular_trading_flag", 0)) else 0.0
    circular_penalty += 5.0 if int(features.get("revenue_inflation_flag", 0)) else 0.0
    penalty_total = _clip(litigation_penalty + sector_penalty + circular_penalty, 0.0, 24.0)

    gst_bonus = (float(features.get("gst_compliance_score", 50.0)) - 50.0) * 0.06
    base_floor = 22.0
    credit_score = _clip(base_floor + positive_score - penalty_total + gst_bonus, 0.0, 100.0)

    # All values are assumed in INR crores.
    revenue = float(financials.get("revenue") or 0.0)
    ebitda = float(financials.get("ebitda") or 0.0)
    cap_by_revenue = 0.25 * revenue
    cap_by_ebitda = 4.0 * ebitda
    raw_limit = min(cap_by_revenue, cap_by_ebitda)
    if credit_score >= 75:
        band_mult = 0.95
    elif credit_score >= 60:
        band_mult = 0.72
    elif credit_score >= 45:
        band_mult = 0.48
    else:
        band_mult = 0.22
    recommended_loan_limit = round(max(0.0, raw_limit * band_mult), 2)

    base_rate = float(scoring_cfg.get("base_rate", 9.5))
    max_risk_premium = float(scoring_cfg.get("max_risk_premium", 5.0))
    volatility_penalty = _clip(1.1 - float(features.get("cashflow_stability", 1.0)), 0.0, 1.2)
    risk_premium = round(max(0.8, max_risk_premium * (1 - credit_score / 100.0) + volatility_penalty), 2)
    recommended_interest_rate = round(base_rate + risk_premium, 2)

    score_band = (
        "strong_credit" if credit_score >= 75 else
        "acceptable_moderate_risk" if credit_score >= 60 else
        "weak_elevated_risk" if credit_score >= 45 else
        "high_risk"
    )

    return {
        "credit_score": round(credit_score, 2),
        "score_band": score_band,
        "loan_limit_cap_revenue_25pct": round(cap_by_revenue, 2),
        "loan_limit_cap_ebitda_4x": round(cap_by_ebitda, 2),
        "recommended_loan_limit": recommended_loan_limit,
        "risk_premium": risk_premium,
        "base_rate": round(base_rate, 2),
        "recommended_interest_rate": recommended_interest_rate,
        "score_audit": {
            "raw_features": features,
            "normalized_positive_factors": {
                "leverage": round(leverage, 4),
                "profitability": round(profitability, 4),
                "cash_stability": round(cash_stability, 4),
                "growth": round(growth, 4),
                "coverage": round(coverage, 4),
                "governance": round(governance, 4),
                "sentiment": round(_clip(float(features.get("news_sentiment_score", 50.0)), 0.0, 100.0), 4),
            },
            "weighted_positive_contributions": {k: round(v, 4) for k, v in positive_components.items()},
            "penalties_applied": {
                "litigation_penalty": round(litigation_penalty, 4),
                "sector_penalty": round(sector_penalty, 4),
                "circular_penalty": round(circular_penalty, 4),
                "penalty_total_capped": round(penalty_total, 4),
            },
            "bonuses": {"gst_bonus": round(gst_bonus, 4)},
            "score_assembly": {
                "base_floor": base_floor,
                "positive_score": round(positive_score, 4),
                "pre_clip_score": round(base_floor + positive_score - penalty_total + gst_bonus, 4),
                "final_credit_score": round(credit_score, 4),
            },
            "reason_low_score": (
                "Score impacted primarily by combined penalties and weak stability/coverage"
                if credit_score < 45
                else "Score calibrated within moderate/strong bands"
            ),
        },
    }
