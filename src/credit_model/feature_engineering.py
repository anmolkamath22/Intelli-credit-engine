"""Credit feature engineering for recommendation engine."""

from __future__ import annotations

import pandas as pd


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def build_credit_features(
    financials: dict,
    financial_trends: dict,
    research: dict,
    bank_df: pd.DataFrame | None,
    officer_inputs: dict,
    gst_signals: dict,
    circular_flags: dict,
) -> dict:
    """Combine financial, behavioral, legal, synthetic, and qualitative signals."""
    revenue = float(financials.get("revenue") or 0.0)
    net_profit = float(financials.get("net_profit") or 0.0)
    debt = float(financials.get("debt") or 0.0)
    assets = float(financials.get("total_assets") or 0.0)
    liabilities = float(financials.get("total_liabilities") or 0.0)
    equity = max(assets - liabilities, 0.0)
    ebitda = float(financials.get("ebitda") or 0.0)
    revenue_prev = float(financials.get("revenue_prev") or 0.0)

    if bank_df is not None and not bank_df.empty and {"monthly_inflow", "monthly_outflow", "average_balance"}.issubset(bank_df.columns):
        inflow = bank_df["monthly_inflow"].astype(float)
        outflow = bank_df["monthly_outflow"].astype(float)
        balance = bank_df["average_balance"].astype(float)
        net = inflow - outflow
        volatility = float(net.std(ddof=0) / (abs(net.mean()) + 1e-6))
        avg_ratio = float(balance.mean() / (outflow.mean() + 1e-6))
    else:
        volatility = 0.0
        avg_ratio = 0.0

    management_risk_score = max(
        0.0,
        min(
            100.0,
            (1 - float(officer_inputs.get("management_credibility", 0.6))) * 45
            + float(officer_inputs.get("inventory_build_up", 0.4)) * 25
            + float(officer_inputs.get("supply_chain_risk", 0.4)) * 30,
        ),
    )
    sector_risk_map = {"low": 25.0, "moderate": 55.0, "high": 80.0}
    sector_risk_score = sector_risk_map.get(str(research.get("sector_risk", "moderate")).lower(), 55.0)

    features = {
        "debt_to_equity": round(_safe_div(debt, equity), 4),
        "profit_margin": round(_safe_div(net_profit, revenue), 4),
        "revenue_growth": round(_safe_div(revenue - revenue_prev, revenue_prev), 4) if revenue_prev else 0.0,
        "revenue_cagr_5y": float(financial_trends.get("revenue_cagr_5y", 0.0)),
        "ebitda_cagr_5y": float(financial_trends.get("ebitda_cagr_5y", 0.0)),
        "net_profit_cagr_5y": float(financial_trends.get("net_profit_cagr_5y", 0.0)),
        "debt_reduction_rate": float(financial_trends.get("debt_reduction_rate", 0.0)),
        "cashflow_stability": round(1.0 / (1.0 + volatility), 4),
        "litigation_risk_score": float(research.get("litigation_risk_score", 0.0)),
        "news_sentiment_score": float(research.get("news_sentiment_score", 50.0)),
        "management_risk_score": round(management_risk_score, 4),
        "sector_risk_score": round(sector_risk_score, 2),
        "average_balance_ratio": round(avg_ratio, 4),
        "interest_coverage": round(_safe_div(ebitda, max(1.0, debt * 0.09)), 4),
        "gst_compliance_score": float(gst_signals.get("gst_compliance_score", 0.0)),
        "circular_trading_flag": int(circular_flags.get("circular_trading_flag", 0)),
        "revenue_inflation_flag": int(circular_flags.get("revenue_inflation_flag", 0)),
    }
    return features
