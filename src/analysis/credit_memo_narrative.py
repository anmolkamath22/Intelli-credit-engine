"""Narrative builder for detailed credit memo sections."""

from __future__ import annotations

from typing import Any


def build_credit_memo_narrative(
    company: str,
    financials: dict[str, Any],
    trends: dict[str, Any],
    validated_financials: dict[str, Any],
    research: dict[str, Any],
    features: dict[str, Any],
    scoring: dict[str, Any],
) -> dict[str, str]:
    def _rv_float(key: str) -> float | None:
        latest_ratios = validated_financials.get("latest_ratios", {}) or {}
        x = latest_ratios.get(key, {}) if isinstance(latest_ratios.get(key, {}), dict) else {}
        if x.get("value") is None:
            return None
        return float(x["value"])

    def _rv(key: str) -> str:
        x = _rv_float(key)
        if x is None:
            return "Not available (insufficient reliable denominator/source)."
        if "margin" in key or "cagr" in key:
            return f"{x * 100:.2f}%"
        return f"{x:.2f}"

    years = validated_financials.get("years", [])
    years_str = f"over the periods {years[0]} to {years[-1]}" if len(years) > 1 else "recently"

    # Financial Trend Narrative
    rev_cagr = float(trends.get("revenue_cagr_5y", 0.0))
    pat_cagr = float(trends.get("net_profit_cagr_5y", 0.0))
    ebitda_cagr = float(trends.get("ebitda_cagr_5y", 0.0))
    
    rev_trend_desc = "shown robust growth" if rev_cagr > 0.05 else ("remained broadly stable" if rev_cagr > -0.05 else "contracted")
    pat_trend_desc = "improved steadily" if pat_cagr > 0.05 else ("shown volatility" if pat_cagr > -0.05 else "declined significantly")
    
    fin_trend_narrative = (
        f"The company’s revenue has {rev_trend_desc} {years_str}, posting a CAGR of {rev_cagr * 100:.2f}%. "
        f"Simultaneously, net profitability has {pat_trend_desc} with a CAGR of {pat_cagr * 100:.2f}%. "
        f"Operating efficiency, as measured by EBITDA, recorded a CAGR of {ebitda_cagr * 100:.2f}%. "
        f"The EBITDA margin has moved from {float(trends.get('ebitda_margin_first', 0.0)) * 100:.2f}% "
        f"in {years[0] if years else 'the initial period'} to {float(trends.get('ebitda_margin_last', 0.0)) * 100:.2f}% in {years[-1] if years else 'the latest period'}. "
        "Overall, the financial trajectory indicates a business model that is " + ("scaling well." if rev_cagr > 0 else "facing growth headwinds.")
    )

    # Liquidity & Leverage Narrative
    debt_trend = str(trends.get("debt_trend", "stable"))
    debt_change = float(trends.get("debt_change_rate", 0.0)) * 100
    de = _rv_float("debt_to_equity")
    de_str = _rv("debt_to_equity")
    
    leverage_desc = "low" if de is not None and de < 1.0 else ("moderate" if de is not None and de < 2.0 else "high")
    debt_note = (
        f"but the sharp {debt_trend} in debt by {debt_change:.2f}% warrants monitoring."
        if debt_change > 20 else f"and debt levels remain {debt_trend}."
    )
    
    cr = _rv_float("current_ratio")
    cr_str = _rv("current_ratio")
    liquidity_desc = "adequate" if cr is not None and cr >= 1.0 else "tight"
    
    liq_lev_narrative = (
        f"Leverage remains {leverage_desc} with a Debt/Equity ratio of {de_str}. "
        f"The company's reliance on external borrowings is evident, {debt_note} "
        f"On the liquidity front, the current ratio stands at {cr_str}, suggesting {liquidity_desc} short-term payment capacity. "
        f"The Debt/EBITDA ratio is {_rv('debt_to_ebitda')}, reflecting the company's capability to service its obligations from operating cash flows."
    )

    # Industry & Sector Narrative
    sector_risk = str(research.get('sector_risk', 'moderate')).upper()
    headwinds = research.get('sector_headwinds', [])
    industry_narrative = (
        f"The overarching sector risk profile is evaluated as {sector_risk}. "
        f"The industry environment currently presents several challenges, including {', '.join(headwinds) if headwinds else 'no major evident headwinds'}. "
        f"Furthermore, broader market signals and news sentiment indicate a score of {float(features.get('news_sentiment_score', 50.0)):.2f}/100, "
        "implying a " + ("stable" if float(features.get('news_sentiment_score', 50.0)) >= 50 else "cautious") + " outlook from external observers."
    )

    # Litigation Assessment Narrative
    lit_count = int(float(research.get('litigation_count', 0)))
    lit_score = float(research.get('litigation_risk_score', 0.0))
    lit_desc = "manageable" if lit_score < 40 else ("moderate but requires tracking" if lit_score < 70 else "severe and poses a material threat")
    litigation_narrative = (
        f"The current legal exposure appears {lit_desc}. We have identified {lit_count} active or recent litigation events, "
        f"yielding a composite litigation risk score of {lit_score:.2f}/100. "
        f"{'Recurring labour or operational matters should be closely tracked.' if lit_count > 0 else 'There are no significant legal disputes observed.'}"
    )
    
    # Promoter & Management Narrative
    promoter_risk = float(research.get("promoter_risk", 0.0))
    mgmt_risk = float(features.get("management_risk_score", 0.0))
    mgmt_narrative = (
        f"Management quality and corporate governance show a composite risk score of {mgmt_risk:.2f}/100, "
        f"while promoter background checks indicate a risk layer of {promoter_risk:.2f}/100. "
        "There are " + ("no apparent severe governance red flags." if mgmt_risk < 50 else "some governance concerns that require heightened scrutiny.")
    )

    # Final Recommendation
    c_score = float(scoring.get('credit_score', 0.0))
    loan_limit = float(scoring.get('recommended_loan_limit', 0.0))
    rate = float(scoring.get('recommended_interest_rate', 0.0))
    conclusion = "approved" if c_score >= 50 else "rejected"
    
    decision_narrative = (
        f"Based on the holistic evaluation of {company}'s financial stability, operating performance, and external risk factors, "
        f"the final aggregated credit score is {c_score:.2f} out of 100. "
        f"Consequently, the facility request is recommended to be {conclusion}. "
        f"We propose a maximum optimal loan limit of INR {loan_limit:.2f} Crores, priced at an interest rate of {rate:.2f}% per annum. "
        "The decision is structurally weighted by the core financial trajectory, current leverage profile, legal contingencies, and management governance metrics."
    )

    return {
        "financial_trend_analysis": fin_trend_narrative,
        "liquidity_leverage_assessment": liq_lev_narrative,
        "promoter_management_assessment": mgmt_narrative,
        "industry_sector_outlook": industry_narrative,
        "litigation_assessment": litigation_narrative,
        "final_recommendation": decision_narrative,
    }

