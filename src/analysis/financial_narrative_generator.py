"""Generate human-readable narrative from financial trends."""

from __future__ import annotations


def generate_financial_narrative(company: str, trends: dict, history: dict) -> list[str]:
    """Create concise analyst-style commentary for CAM."""
    years = history.get("years", [])
    rows = history.get("yearly_data", [])
    if not years or not rows:
        return ["Insufficient multi-year data to produce robust financial trend commentary."]

    first = rows[0]
    last = rows[-1]
    rev_cagr = float(trends.get("revenue_cagr_5y", 0.0)) * 100
    ebitda_cagr = float(trends.get("ebitda_cagr_5y", 0.0)) * 100
    pat_cagr = float(trends.get("net_profit_cagr_5y", 0.0)) * 100
    debt_reduction = float(trends.get("debt_reduction_rate", 0.0)) * 100

    notes = [
        (
            f"Revenue trend ({years[0]} to {years[-1]}): CAGR of {rev_cagr:.2f}% "
            f"with revenue moving from INR {float(first.get('revenue') or 0.0):,.2f} crore "
            f"to INR {float(last.get('revenue') or 0.0):,.2f} crore."
        ),
        (
            f"Operating profitability: EBITDA CAGR of {ebitda_cagr:.2f}% and net profit CAGR of {pat_cagr:.2f}% "
            f"over the observed period."
        ),
        (
            f"Leverage trend: debt changed from INR {float(first.get('debt') or 0.0):,.2f} crore "
            f"to INR {float(last.get('debt') or 0.0):,.2f} crore "
            f"(debt reduction rate {debt_reduction:.2f}%)."
        ),
        (
            f"Margin behavior: EBITDA margin moved from {float(trends.get('ebitda_margin_first', 0.0)) * 100:.2f}% "
            f"to {float(trends.get('ebitda_margin_last', 0.0)) * 100:.2f}%."
        ),
        f"Overall inference for {company}: financial trajectory should be assessed jointly with legal, sector, and cashflow-risk indicators.",
    ]
    return notes

