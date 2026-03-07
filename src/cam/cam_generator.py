"""Structured CAM payload generator (JSON-first, renderer-agnostic)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.analysis.credit_memo_narrative import build_credit_memo_narrative


def _to_float(x: object, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


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
    if "credit_features" in s or "financial_features" in s:
        return "feature_summary"
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
            return "/".join(parts[idx: idx + 2]) if idx + 1 < len(parts) else folder
    return p.name


def _financial_table(history: dict) -> dict:
    years = [str(y) for y in history.get("years", [])]
    rows = history.get("yearly_data", [])
    if not years or not rows:
        return {
            "headers": ["Metric", "FY24"],
            "rows": [
                ["Revenue", "NA"],
                ["EBITDA", "NA"],
                ["Net Profit", "NA"],
                ["Debt", "NA"],
                ["Debt/Equity", "NA"],
                ["EBITDA Margin", "NA"],
            ],
        }
    idx = {str(r.get("year")): r for r in rows}

    def _metric_row(name: str, key: str) -> list[str]:
        vals: list[str] = []
        for y in years:
            v = _to_float(idx.get(y, {}).get(key), 0.0)
            vals.append(f"{v:,.2f}")
        return [name] + vals

    debt_equity = ["Debt/Equity"]
    ebitda_margin = ["EBITDA Margin"]
    for y in years:
        r = idx.get(y, {})
        assets = _to_float(r.get("total_assets"), 0.0)
        liabilities = _to_float(r.get("total_liabilities"), 0.0)
        equity = max(assets - liabilities, 1e-6)
        debt = _to_float(r.get("debt"), 0.0)
        rev = _to_float(r.get("revenue"), 0.0)
        ebitda = _to_float(r.get("ebitda"), 0.0)
        debt_equity.append(f"{(debt / equity):.2f}")
        ebitda_margin.append(f"{(ebitda / rev * 100.0 if rev else 0.0):.2f}%")

    return {
        "headers": ["Metric"] + years,
        "rows": [
            _metric_row("Revenue", "revenue"),
            _metric_row("EBITDA", "ebitda"),
            _metric_row("Net Profit", "net_profit"),
            _metric_row("Debt", "debt"),
            debt_equity,
            ebitda_margin,
        ],
    }


def build_cam_payload(
    company: str,
    financials: dict[str, Any],
    research: dict[str, Any],
    features: dict[str, Any],
    scoring: dict[str, Any],
    trace: dict[str, Any],
    financial_history: dict[str, Any] | None = None,
    financial_trends: dict[str, Any] | None = None,
    trend_narrative: list[str] | None = None,
    dataset_presence: dict[str, Any] | None = None,
    validated_financials: dict[str, Any] | None = None,
    cam_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build structured CAM payload for deterministic rendering."""
    financial_history = financial_history or {}
    financial_trends = financial_trends or {}
    trend_narrative = trend_narrative or []
    dataset_presence = dataset_presence or {}
    validated_financials = validated_financials or {}
    cam_evidence = cam_evidence or []

    credit_score = _to_float(scoring.get("credit_score"), 0.0)
    loan_limit = _to_float(scoring.get("recommended_loan_limit"), 0.0)
    rate = _to_float(scoring.get("recommended_interest_rate"), _to_float(scoring.get("base_rate"), 9.5))

    years = financial_history.get("years", [])
    trends_text = " ".join(trend_narrative).strip()
    if not trends_text:
        rev_cagr = _to_float(financial_trends.get("revenue_cagr_5y"), 0.0) * 100
        pat_cagr = _to_float(financial_trends.get("net_profit_cagr_5y"), 0.0) * 100
        debt_chg = _to_float(financial_trends.get("debt_change_rate"), 0.0) * 100
        debt_trend = str(financial_trends.get("debt_trend", "stable"))
        trends_text = (
            f"Revenue CAGR ({years[0]}-{years[-1]}) is {rev_cagr:.2f}% and net profit CAGR is {pat_cagr:.2f}%. "
            f"Debt is {debt_trend} with a total change of {debt_chg:.2f}% over the same period."
            if years
            else "Insufficient multi-year trends available."
        )

    source_types: list[str] = []
    evidence = []

    # 1) Direct mapped evidence from extracted financial table rows (highest priority).
    fin_row_evidence = []
    for row in (financial_history.get("yearly_data", []) or [])[-5:]:
        fy = str(row.get("year", ""))
        src = str(row.get("source", ""))
        stype = _source_type(src)
        if stype not in source_types:
            source_types.append(stype)
        mapped = row.get("source_rows", {}) or {}
        for metric in ["revenue", "ebitda", "net_profit", "debt", "total_assets", "total_liabilities", "finance_cost", "cash_flow"]:
            line = str(mapped.get(metric, "")).strip()
            if line:
                if len(line) > 220:
                    line = line[:217] + "..."
                fin_row_evidence.append(
                    {
                        "source": stype,
                        "reference": _reference_hint(src),
                        "excerpt": f"{fy} [{metric}] {line}",
                        "section_type": "financial",
                    }
                )
        # Fallback to metric snapshot evidence when exact row label text is unavailable.
        snapshot = (
            f"{fy} extracted metrics: revenue={_to_float(row.get('revenue'), 0.0):,.2f}, "
            f"ebitda={_to_float(row.get('ebitda'), 0.0):,.2f}, "
            f"net_profit={_to_float(row.get('net_profit'), 0.0):,.2f}, "
            f"debt={_to_float(row.get('debt'), 0.0):,.2f} (INR Crores)."
        )
        fin_row_evidence.append(
            {
                "source": stype,
                "reference": _reference_hint(src),
                "excerpt": snapshot,
                "section_type": "financial",
            }
        )

    # 2) Litigation summary evidence.
    for idx, cs in enumerate((research.get("case_summary", []) or [])[:4], start=1):
        line = str(cs).strip().replace("\n", " ")
        if len(line) > 220:
            line = line[:217] + "..."
        evidence.append(
            {
                "source": "legal_documents",
                "reference": f"case_summary_{idx}",
                "excerpt": line,
                "section_type": "litigation",
            }
        )
    source_evidence = cam_evidence if cam_evidence else (research.get("supporting_evidence", []) or [])
    for e in source_evidence[:15]:
        src = str(e.get("source", "unknown"))
        stype = _source_type(src)
        if stype not in source_types:
            source_types.append(stype)
        excerpt = str(e.get("chunk", "")).strip().replace("\n", " ")
        if len(excerpt) > 220:
            excerpt = excerpt[:217] + "..."
        evidence.append(
            {
                "source": stype,
                "reference": _reference_hint(src),
                "excerpt": excerpt,
                "section_type": str((e.get("metadata") or {}).get("section_type", "general")),
            }
        )

    # Merge prioritized mapped evidence first.
    evidence = fin_row_evidence[:10] + evidence

    # De-duplicate by excerpt text.
    seen = set()
    deduped = []
    for ev in evidence:
        key = (ev.get("source"), ev.get("reference"), ev.get("excerpt"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ev)
    evidence = deduped[:20]

    if not source_types:
        for k, v in dataset_presence.items():
            if int(v):
                source_types.append(str(k))

    rating = research.get("external_credit_rating") or "Not Available"
    rating_hist = research.get("rating_history") or []
    if rating_hist:
        rating = f"{rating} ({' -> '.join([str(x) for x in rating_hist[:5]])})"

    risk_flags_raw = trace.get("risk_flags", []) or ["No major risk flags identified."]
    risk_flags = [{"flag": str(f), "explanation": "Flag raised from model risk logic and supporting evidence."} for f in risk_flags_raw]
    narrative = build_credit_memo_narrative(
        company=company,
        financials=financials,
        trends=financial_trends,
        validated_financials=validated_financials,
        research=research,
        features=features,
        scoring=scoring,
    )

    return {
        "title": "Credit Appraisal Memo",
        "company_name": company,
        "reporting_note": "All financial values are reported in INR Crores unless otherwise stated.",
        "executive_summary": (
            f"Final credit score is {credit_score:.2f}/100. "
            f"Recommended loan limit is INR {loan_limit:,.2f} Crores at {rate:.2f}% per annum. "
            f"Assessment uses financial trends, legal/news signals, synthetic behavior signals (when required), and decision trace explainability."
        ),
        "company_overview": (
            f"The evaluation covers available company datasets with primary evidence from: "
            f"{', '.join(source_types) if source_types else 'available uploaded datasets'}. "
            f"Document count processed: {int(_to_float(financials.get('document_count'), 0))}. "
            f"External credit rating observed: {rating}."
        ),
        "financial_performance": {
            "narrative": (
                f"Years analyzed: {', '.join(years) if years else 'Not available'}. "
                f"Latest revenue: INR {_to_float(financials.get('revenue'), 0.0):,.2f} Crores; "
                f"latest EBITDA: INR {_to_float(financials.get('ebitda'), 0.0):,.2f} Crores. "
                f"{trends_text}"
            ),
            "table": _financial_table(financial_history),
        },
        "promoter_analysis": (
            f"Promoter risk score: {_to_float(research.get('promoter_risk'), 0.0):.2f}/100. "
            f"Management risk score: {_to_float(features.get('management_risk_score'), 0.0):.2f}/100. "
            f"Rating rationale: {research.get('rating_rationale') or 'Not available in uploaded data.'}"
        ),
        "industry_outlook": (
            f"Sector risk assessment is {str(research.get('sector_risk', 'moderate')).upper()}. "
            f"Headwinds observed: {', '.join(research.get('sector_headwinds', []) or ['none'])}."
        ),
        "litigation_profile": (
            f"Litigation count: {int(_to_float(research.get('litigation_count'), 0))}. "
            f"Litigation risk score: {_to_float(research.get('litigation_risk_score'), 0.0):.2f}/100."
        ),
        "risk_flags": risk_flags,
        "decision_logic": (
            f"{trace.get('reasoning_summary') or 'The credit decision is weighted primarily by the company’s core financial trajectory, risk indicators, and cashflow consistency.'} "
            f"Notably, circular trading risk flag is {'triggered' if int(_to_float(features.get('circular_trading_flag'), 0)) else 'clear'}, "
            f"and revenue inflation flag is {'triggered' if int(_to_float(features.get('revenue_inflation_flag'), 0)) else 'clear'}. "
            f"The primary synthesis relies heavily on {', '.join(source_types) if source_types else 'the available verified documents'}."
        ),
        "final_credit_score": f"{credit_score:.2f} / 100",
        "recommended_loan_limit_crore": f"{loan_limit:.2f}",
        "interest_rate_percent": f"{rate:.2f}",
        "supporting_evidence": evidence,
        "financial_trend_analysis": narrative.get("financial_trend_analysis", ""),
        "liquidity_leverage_assessment": narrative.get("liquidity_leverage_assessment", ""),
        "promoter_management_assessment": narrative.get("promoter_management_assessment", ""),
        "industry_sector_outlook": narrative.get("industry_sector_outlook", ""),
        "litigation_assessment": narrative.get("litigation_assessment", ""),
        "final_recommendation": narrative.get("final_recommendation", ""),
        "validated_financials": validated_financials,
        "metadata": {
            "source_types_used": source_types,
            "dataset_presence": dataset_presence,
            "loan_policy_caps": {
                "cap_25pct_revenue_crore": round(_to_float(scoring.get("loan_limit_cap_revenue_25pct"), 0.0), 2),
                "cap_4x_ebitda_crore": round(_to_float(scoring.get("loan_limit_cap_ebitda_4x"), 0.0), 2),
            },
        },
    }
