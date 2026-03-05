"""CAM generator combining scoring and trace outputs."""

from __future__ import annotations

from pathlib import Path


def _to_float(x: object, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _fmt_inr(x: object) -> str:
    v = _to_float(x, 0.0)
    return f"INR {v:,.2f}"


def _fmt_pct(x: object, scale: float = 1.0) -> str:
    v = _to_float(x, 0.0) * scale
    return f"{v:.2f}%"


def _fmt_num(x: object, digits: int = 2) -> str:
    v = _to_float(x, 0.0)
    return f"{v:,.{digits}f}"


def _build_financial_table(history: dict) -> list[str]:
    years = history.get("years", [])
    rows = history.get("yearly_data", [])
    if not years or not rows:
        return ["Financial history table unavailable due to missing multi-year annual report extraction."]

    idx = {str(r.get("year")): r for r in rows}
    hdr = "| Metric | " + " | ".join(years) + " |"
    sep = "| --- | " + " | ".join(["---"] * len(years)) + " |"

    def metric_row(label: str, key: str, pct: bool = False) -> str:
        vals = []
        for y in years:
            r = idx.get(y, {})
            v = _to_float(r.get(key), 0.0)
            vals.append(f"{(v * 100):.2f}%" if pct else f"{v:,.2f}")
        return "| " + label + " | " + " | ".join(vals) + " |"

    def debt_equity_row() -> str:
        vals = []
        for y in years:
            r = idx.get(y, {})
            assets = _to_float(r.get("total_assets"), 0.0)
            liab = _to_float(r.get("total_liabilities"), 0.0)
            equity = max(assets - liab, 1e-6)
            debt = _to_float(r.get("debt"), 0.0)
            vals.append(f"{(debt / equity):.2f}")
        return "| Debt/Equity | " + " | ".join(vals) + " |"

    def ebitda_margin_row() -> str:
        vals = []
        for y in years:
            r = idx.get(y, {})
            rev = _to_float(r.get("revenue"), 0.0)
            ebt = _to_float(r.get("ebitda"), 0.0)
            vals.append(f"{(ebt / rev * 100 if rev else 0.0):.2f}%")
        return "| EBITDA Margin | " + " | ".join(vals) + " |"

    return [
        "Financial Performance (INR Crores)",
        hdr,
        sep,
        metric_row("Revenue", "revenue"),
        metric_row("EBITDA", "ebitda"),
        metric_row("Net Profit", "net_profit"),
        metric_row("Debt", "debt"),
        debt_equity_row(),
        ebitda_margin_row(),
    ]


def _source_type(src: str) -> str:
    s = src.lower()
    if "annual_reports" in s:
        return "annual_reports"
    if "gst_returns" in s or "synthetic_gst_features" in s:
        return "gst_returns"
    if "bank_statements" in s or "synthetic_bank_features" in s:
        return "bank_statements"
    if "legal_documents" in s or "litigation" in s:
        return "legal_documents"
    if "news_documents" in s or "news" in s:
        return "news_documents"
    if "financial_statements" in s:
        return "financial_statements"
    if "balance_sheets" in s:
        return "balance_sheets"
    if "research_summary" in s:
        return "research_summary"
    if "credit_features" in s:
        return "credit_features"
    return "other_documents"


def _reference_hint(src: str) -> str:
    p = Path(src)
    parts = p.parts
    for folder in [
        "annual_reports",
        "financial_statements",
        "balance_sheets",
        "gst_returns",
        "bank_statements",
        "legal_documents",
        "news_documents",
    ]:
        if folder in parts:
            idx = parts.index(folder)
            tail = "/".join(parts[idx: idx + 2]) if idx + 1 < len(parts) else folder
            return tail
    return p.name


def build_cam_sections(
    company: str,
    financials: dict,
    research: dict,
    features: dict,
    scoring: dict,
    trace: dict,
    financial_history: dict | None = None,
    financial_trends: dict | None = None,
    trend_narrative: list[str] | None = None,
    dataset_presence: dict | None = None,
) -> dict:
    """Build CAM sections in narrative format for readable report rendering."""
    credit_score = _to_float(scoring.get("credit_score"), 0.0)
    risk_premium = _to_float(scoring.get("risk_premium"), 0.0)
    interest_rate = 9.5 + risk_premium
    loan_limit = _to_float(scoring.get("recommended_loan_limit"), 0.0)
    financial_history = financial_history or {"years": [], "yearly_data": []}
    financial_trends = financial_trends or {}
    trend_narrative = trend_narrative or []
    dataset_presence = dataset_presence or {}

    risk_flags = trace.get("risk_flags", []) or ["No major risk flags identified from current inputs."]
    headwinds = research.get("sector_headwinds", []) or ["No major sector headwinds identified from available data."]
    rating_hist = research.get("rating_history", [])
    evidence_rows = research.get("supporting_evidence", [])[:5]
    evidence_lines = []
    source_types: list[str] = []
    for e in evidence_rows:
        src = str(e.get("source", "unknown"))
        stype = _source_type(src)
        if stype not in source_types:
            source_types.append(stype)
        ref = _reference_hint(src)
        snippet = str(e.get("chunk", "")).strip().replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:157] + "..."
        evidence_lines.append(f"Source Type: {stype} | Reference: {ref} | Evidence: {snippet}")
    if not evidence_lines:
        evidence_lines = ["No RAG evidence snippets available from current retrieved corpus."]
    if not source_types:
        for k, v in dataset_presence.items():
            if v:
                source_types.append(k)

    attribution_lines = [
        "Conclusion source mapping (dataset-level, no hardcoded absolute paths):",
        f"Primary sources used: {', '.join(source_types) if source_types else 'Not available'}",
    ]
    for k in [
        "annual_reports",
        "financial_statements",
        "balance_sheets",
        "gst_returns",
        "bank_statements",
        "legal_documents",
        "news_documents",
    ]:
        status = "available" if int(dataset_presence.get(k, 0)) else "missing/synthetic fallback used"
        attribution_lines.append(f"{k}: {status}")
    rating_text = research.get("external_credit_rating") or "Not available"
    if rating_hist:
        rating_text = f"{rating_text} (history: {' -> '.join([str(x) for x in rating_hist[:5]])})"

    return {
        "Executive Summary": (
            f"Credit appraisal for {company}: final credit score {credit_score:.2f}/100, "
            f"recommended loan limit INR {loan_limit:,.2f} crore, and recommended interest rate "
            f"{_to_float(scoring.get('recommended_interest_rate'), interest_rate):.2f}% p.a. "
            "All financial figures are reported in INR Crores unless otherwise stated."
        ),
        "Company Overview": (
            f"{company} was evaluated using locally ingested financial and risk documents. "
            f"Document count reviewed: {_fmt_num(financials.get('document_count'), 0)}. "
            f"External credit rating (if available): {rating_text}."
        ),
        "5-Year Financial Performance": (
            f"Years analyzed: {', '.join(financial_history.get('years', [])) or 'Not available'}. "
            f"Latest year revenue: {_fmt_inr(financials.get('revenue'))} crore and EBITDA: {_fmt_inr(financials.get('ebitda'))} crore."
        ),
        "Financial Ratio Table": _build_financial_table(financial_history),
        "Financial Trend Analysis": trend_narrative or [
            "Insufficient data for detailed 5-year trend interpretation."
        ],
        "Financial Strength": (
            f"Revenue: {_fmt_inr(financials.get('revenue'))}; Net profit: {_fmt_inr(financials.get('net_profit'))}; "
            f"EBITDA: {_fmt_inr(financials.get('ebitda'))}; Debt: {_fmt_inr(financials.get('debt'))}. "
            f"Total assets: {_fmt_inr(financials.get('total_assets'))}; Total liabilities: {_fmt_inr(financials.get('total_liabilities'))}. "
            f"Debt-to-equity: {_fmt_num(features.get('debt_to_equity'))}; Profit margin: {_fmt_pct(features.get('profit_margin'), 100)}; "
            f"Interest coverage: {_fmt_num(features.get('interest_coverage'))}x."
        ),
        "Promoter Analysis": (
            f"Promoter risk score: {_fmt_num(research.get('promoter_risk'))}/100. "
            f"Management risk score: {_fmt_num(features.get('management_risk_score'))}/100. "
            f"Rating rationale: {research.get('rating_rationale') or 'Not available from current dataset.'}"
        ),
        "Industry Conditions": (
            f"Sector risk assessment: {str(research.get('sector_risk', 'moderate')).upper()}. "
            f"Observed headwinds: {'; '.join([str(x) for x in headwinds])}."
        ),
        "Litigation Profile": (
            f"Litigation count: {_fmt_num(research.get('litigation_count'), 0)}. "
            f"Litigation risk score: {_fmt_num(research.get('litigation_risk_score'))}/100. "
            f"Case summary: {research.get('case_summary') or 'No detailed case summary in provided files.'}"
        ),
        "Management Assessment": (
            f"Cashflow stability: {_fmt_num(features.get('cashflow_stability'))} (0 to 1 scale, higher is better). "
            f"GST compliance score: {_fmt_num(features.get('gst_compliance_score'))}/100. "
            f"News sentiment score: {_fmt_num(features.get('news_sentiment_score'))}/100."
        ),
        "Risk Flags": [str(x) for x in risk_flags],
        "Evidence Attribution": attribution_lines,
        "Supporting Evidence (RAG)": evidence_lines,
        "Decision Logic": (
            f"{trace.get('reasoning_summary') or 'Decision logic derived from weighted financial, legal, sentiment, and management factors.'} "
            f"Primary conclusion drivers were sourced from: {', '.join(source_types) if source_types else 'available ingested datasets'}. "
            f"Model penalties were applied for circular-trading flag="
            f"{int(_to_float(features.get('circular_trading_flag'), 0))} and revenue-inflation flag="
            f"{int(_to_float(features.get('revenue_inflation_flag'), 0))}."
        ),
        "Final Credit Score": f"{credit_score:.2f} / 100",
        "Credit Rating (External)": rating_text,
        "Recommended Loan Limit": (
            f"INR {loan_limit:,.2f} crore (model output). "
            f"Policy caps: 25% of annual revenue={_to_float(scoring.get('loan_limit_cap_revenue_25pct'), 0.0):,.2f} crore; "
            f"4x EBITDA={_to_float(scoring.get('loan_limit_cap_ebitda_4x'), 0.0):,.2f} crore."
        ),
        "Interest Rate Recommendation": (
            f"{_to_float(scoring.get('recommended_interest_rate'), interest_rate):.2f}% per annum "
            f"(Base {_to_float(scoring.get('base_rate'), 9.5):.2f}% + Risk premium {risk_premium:.2f}%)."
        ),
    }
