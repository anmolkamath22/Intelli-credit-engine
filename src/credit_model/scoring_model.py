"""Transparent credit scoring model."""

from __future__ import annotations


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def score_credit(features: dict, financials: dict, scoring_cfg: dict, research: dict, entity_profile: dict | None = None) -> dict:
    """Compute calibrated credit score and evaluate requested loan + requested rate."""
    entity_profile = entity_profile or {}
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

    # Internal supportability caps (INR Crores) used to evaluate requested amount.
    revenue = float(financials.get("revenue") or 0.0)
    ebitda = float(financials.get("ebitda") or 0.0)
    cap_by_revenue = 0.25 * revenue
    cap_by_ebitda = 4.0 * ebitda
    supportability_cap = round(max(0.0, min(cap_by_revenue, cap_by_ebitda)), 2)
    requested_loan_amount = float(entity_profile.get("loan_amount") or entity_profile.get("requested_loan_amount") or 0.0)
    requested_interest_rate = float(entity_profile.get("interest_rate") or entity_profile.get("requested_interest_rate") or 0.0)
    loan_type = str(entity_profile.get("loan_type") or "NA")
    tenure_months = int(float(entity_profile.get("loan_tenure_months") or entity_profile.get("tenure") or 0))

    base_rate = float(scoring_cfg.get("base_rate", 9.5))
    max_risk_premium = float(scoring_cfg.get("max_risk_premium", 5.0))
    volatility_penalty = _clip(1.1 - float(features.get("cashflow_stability", 1.0)), 0.0, 1.2)
    risk_premium = round(max(0.8, max_risk_premium * (1 - credit_score / 100.0) + volatility_penalty), 2)
    recommended_interest_rate = round(base_rate + risk_premium, 2)

    if requested_interest_rate <= 0:
        requested_interest_rate = recommended_interest_rate

    score_band = (
        "strong_credit" if credit_score >= 75 else
        "acceptable_moderate_risk" if credit_score >= 60 else
        "weak_elevated_risk" if credit_score >= 45 else
        "high_risk"
    )

    support_ratio = (requested_loan_amount / supportability_cap) if supportability_cap > 0 else 999.0
    requested_amount_supportability = (
        "fully_supportable" if support_ratio <= 1.0 else
        "borderline" if support_ratio <= 1.25 else
        "unsupported"
    )

    conditions: list[str] = []
    if requested_amount_supportability != "fully_supportable":
        conditions.append("Reduce sanctioned amount or provide additional collateral support.")
    if float(features.get("cashflow_stability", 0.0)) < 0.45:
        conditions.append("Monthly cash-flow monitoring and tighter review covenant.")
    if float(features.get("litigation_risk_score", 0.0)) >= 55:
        conditions.append("Legal event monitoring covenant with immediate disclosure triggers.")
    if float(features.get("management_risk_score", 0.0)) >= 60:
        conditions.append("Quarterly governance and management conduct review.")
    if int(features.get("circular_trading_flag", 0)) or int(features.get("revenue_inflation_flag", 0)):
        conditions.append("Enhanced transaction audit and escrow-style cash controls.")

    high_uncertainty = (
        str(research.get("news_risk_assessment", "")).startswith("unknown")
        or str(research.get("litigation_risk_status", "")).startswith("unknown")
    )
    if high_uncertainty:
        conditions.append("Insufficient external evidence: require enhanced due diligence before full disbursal.")

    if credit_score < 45 or requested_amount_supportability == "unsupported":
        decision_status = "reject"
    elif requested_amount_supportability == "borderline" or credit_score < 60 or high_uncertainty:
        decision_status = "approve_with_conditions"
    else:
        decision_status = "approve"

    if decision_status == "reject":
        interest_decision = "negotiate_rate"
    elif requested_interest_rate + 0.05 >= recommended_interest_rate:
        interest_decision = "accept_requested_rate"
        recommended_interest_rate = round(requested_interest_rate, 2)
    elif requested_interest_rate < recommended_interest_rate - 0.75:
        interest_decision = "increase_rate"
    else:
        interest_decision = "negotiate_rate"

    approval_rationale = (
        f"Requested amount supportability is {requested_amount_supportability} against internal affordability cap "
        f"(min(25% revenue, 4x EBITDA) = INR {supportability_cap:.2f} Cr). "
        f"Credit score is {credit_score:.2f}/100 with band '{score_band}'. "
        f"Requested rate {requested_interest_rate:.2f}% vs risk-adjusted rate {recommended_interest_rate:.2f}%."
    )

    return {
        "credit_score": round(credit_score, 2),
        "score_band": score_band,
        "loan_type": loan_type,
        "loan_tenure_months": tenure_months,
        "requested_loan_amount": round(requested_loan_amount, 2),
        "requested_interest_rate": round(requested_interest_rate, 2),
        "requested_amount_supportability": requested_amount_supportability,
        "decision_status": decision_status,
        "interest_decision": interest_decision,
        "key_conditions": conditions,
        "approval_rationale": approval_rationale,
        "loan_limit_cap_revenue_25pct": round(cap_by_revenue, 2),
        "loan_limit_cap_ebitda_4x": round(cap_by_ebitda, 2),
        "supportability_cap": supportability_cap,
        # Legacy fields kept for backward compatibility with existing frontend/report readers.
        "recommended_loan_limit": round(requested_loan_amount, 2),
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
            "requested_amount_analysis": {
                "requested_loan_amount": round(requested_loan_amount, 4),
                "supportability_cap": round(supportability_cap, 4),
                "support_ratio": round(support_ratio, 4),
                "requested_amount_supportability": requested_amount_supportability,
            },
            "requested_rate_analysis": {
                "requested_interest_rate": round(requested_interest_rate, 4),
                "risk_adjusted_rate": round(recommended_interest_rate, 4),
                "interest_decision": interest_decision,
            },
            "reason_low_score": (
                "Score impacted primarily by combined penalties and weak stability/coverage"
                if credit_score < 45
                else "Score calibrated within moderate/strong bands"
            ),
        },
    }
