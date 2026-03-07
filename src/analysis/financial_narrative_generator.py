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
    debt_change = float(trends.get("debt_change_rate", 0.0)) * 100
    debt_trend = str(trends.get("debt_trend", "stable"))

    cagr_text = []
    if bool(trends.get("revenue_cagr_valid", True)):
        cagr_text.append(f"Revenue CAGR of {rev_cagr:.2f}%")
    else:
        cagr_text.append("Revenue CAGR not meaningful due to non-positive base/terminal year values")
    if bool(trends.get("ebitda_cagr_valid", True)):
        cagr_text.append(f"EBITDA CAGR of {ebitda_cagr:.2f}%")
    else:
        cagr_text.append("EBITDA CAGR not meaningful due to non-positive base/terminal year values")
    if bool(trends.get("net_profit_cagr_valid", True)):
        cagr_text.append(f"net profit CAGR of {pat_cagr:.2f}%")
    else:
        cagr_text.append("net profit CAGR not meaningful due to non-positive base/terminal year values")

    notes = [
        (
            f"Revenue trend ({years[0]} to {years[-1]}): "
            f"with revenue moving from INR {float(first.get('revenue') or 0.0):,.2f} crore "
            f"to INR {float(last.get('revenue') or 0.0):,.2f} crore."
        ),
        f"Operating profitability trends: {'; '.join(cagr_text)}.",
        (
            f"Leverage trend: debt changed from INR {float(first.get('debt') or 0.0):,.2f} crore "
            f"to INR {float(last.get('debt') or 0.0):,.2f} crore "
            f"({debt_trend}, change rate {debt_change:.2f}%)."
        ),
        (
            f"Margin behavior: EBITDA margin moved from {float(trends.get('ebitda_margin_first', 0.0)) * 100:.2f}% "
            f"to {float(trends.get('ebitda_margin_last', 0.0)) * 100:.2f}%."
        ),
        f"Overall inference for {company}: financial trajectory should be assessed jointly with legal, sector, and cashflow-risk indicators.",
    ]
    return notes
