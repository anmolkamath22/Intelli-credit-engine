"""Deterministic CAM JSON -> LaTeX renderer."""

from __future__ import annotations

from typing import Any

from src.cam.latex_sanitizer import escape_latex
from src.cam.latex_template import get_latex_template


def _paragraph(text: object) -> str:
    return escape_latex(text) + "\n"


def _render_risk_flags(flags: list[dict[str, Any]]) -> str:
    if not flags:
        return r"\begin{itemize}\item No major risk flags identified.\end{itemize}" + "\n"
    out = [r"\begin{itemize}"]
    for f in flags:
        flag = escape_latex(f.get("flag", "Risk Flag"))
        exp = escape_latex(f.get("explanation", ""))
        out.append(rf"\item \textbf{{{flag}}}: {exp}")
    out.append(r"\end{itemize}")
    return "\n".join(out) + "\n"


def _render_evidence(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return r"\begin{itemize}\item No supporting evidence snippets retrieved.\end{itemize}" + "\n"
    out = [r"\begin{itemize}"]
    for ev in evidence:
        src = escape_latex(ev.get("source", "unknown"))
        ref = escape_latex(ev.get("reference", ""))
        excerpt = escape_latex(ev.get("excerpt", ""))
        if ref:
            out.append(rf"\item \textbf{{Source:}} {src} ({ref}) \\ \textit{{Excerpt:}} {excerpt}")
        else:
            out.append(rf"\item \textbf{{Source:}} {src} \\ \textit{{Excerpt:}} {excerpt}")
    out.append(r"\end{itemize}")
    return "\n".join(out) + "\n"


def _render_table(table: dict[str, Any]) -> str:
    headers = [escape_latex(h) for h in table.get("headers", [])]
    rows = table.get("rows", [])
    if not headers:
        return escape_latex("Financial table unavailable.") + "\n"

    col_count = len(headers)
    col_spec = "p{3.2cm} " + " ".join(["p{1.8cm}"] * (col_count - 1))

    out = [
        r"\begin{longtable}{" + col_spec + "}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
        r"\endhead",
    ]
    for row in rows:
        cells = [escape_latex(c) for c in row]
        # Pad/trim for safety.
        if len(cells) < col_count:
            cells.extend([""] * (col_count - len(cells)))
        elif len(cells) > col_count:
            cells = cells[:col_count]
        out.append(" & ".join(cells) + r" \\")
    out.extend([r"\bottomrule", r"\end{longtable}"])
    return "\n".join(out) + "\n"


def render_cam_payload_to_latex(payload: dict[str, Any]) -> str:
    """Render structured CAM payload to a full LaTeX document string."""
    sections: list[str] = []
    sections.append(r"\section*{Executive Summary}" + "\n" + _paragraph(payload.get("executive_summary", "")))
    sections.append(r"\section*{Company Overview}" + "\n" + _paragraph(payload.get("company_overview", "")))

    fp = payload.get("financial_performance", {})
    sections.append(r"\section*{5-Year Financial Performance}" + "\n" + _paragraph(fp.get("narrative", "")))
    sections.append(r"\subsection*{Financial Ratio Table (INR Crores)}" + "\n" + _render_table(fp.get("table", {})))
    sections.append(r"\section*{Financial Trend Analysis}" + "\n" + _paragraph(payload.get("financial_trend_analysis", "")))
    sections.append(r"\section*{Liquidity and Leverage Assessment}" + "\n" + _paragraph(payload.get("liquidity_leverage_assessment", "")))

    sections.append(
        r"\section*{Promoter and Management Assessment}"
        + "\n"
        + _paragraph(payload.get("promoter_management_assessment", payload.get("promoter_analysis", "")))
    )
    sections.append(r"\section*{Industry and Sector Outlook}" + "\n" + _paragraph(payload.get("industry_sector_outlook", payload.get("industry_outlook", ""))))
    sections.append(r"\section*{Litigation Assessment}" + "\n" + _paragraph(payload.get("litigation_assessment", payload.get("litigation_profile", ""))))

    sections.append(r"\section*{Risk Flags}" + "\n" + _render_risk_flags(payload.get("risk_flags", [])))
    sections.append(r"\section*{Decision Rationale}" + "\n" + _paragraph(payload.get("decision_logic", "")))
    sections.append(r"\section*{Final Recommendation}" + "\n" + _paragraph(payload.get("final_recommendation", "")))

    summary_table = {
        "headers": ["Key Output", "Value"],
        "rows": [
            ["Final Credit Score", payload.get("final_credit_score", "")],
            ["Recommended Loan Limit", f"INR {payload.get('recommended_loan_limit_crore', '')} Crores"],
            ["Interest Rate", f"{payload.get('interest_rate_percent', '')}% per annum"],
        ],
    }
    sections.append(r"\section*{Final Recommendation Summary}" + "\n" + _render_table(summary_table))

    sections.append(r"\section*{Supporting Evidence}" + "\n" + _render_evidence(payload.get("supporting_evidence", [])))
    sections.append(r"\section*{Supporting Evidence Appendix}" + "\n" + _render_evidence(payload.get("supporting_evidence", [])))

    template = get_latex_template()
    return (
        template.replace("{TITLE}", escape_latex(payload.get("title", "Credit Appraisal Memo")))
        .replace("{COMPANY\\_NAME}", escape_latex(payload.get("company_name", "")))
        .replace("{REPORTING\\_NOTE}", escape_latex(payload.get("reporting_note", "")))
        .replace("{CONTENT}", "\n".join(sections))
    )
