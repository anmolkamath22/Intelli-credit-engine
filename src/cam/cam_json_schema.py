"""Schema validation for structured CAM payload."""

from __future__ import annotations

from typing import Any


REQUIRED_TOP_LEVEL_FIELDS = [
    "title",
    "company_name",
    "reporting_note",
    "executive_summary",
    "company_overview",
    "financial_performance",
    "promoter_analysis",
    "industry_outlook",
    "litigation_profile",
    "risk_flags",
    "decision_logic",
    "final_credit_score",
    "recommended_loan_limit_crore",
    "interest_rate_percent",
    "supporting_evidence",
]


def validate_cam_payload(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate minimum shape for CAM payload JSON."""
    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL_FIELDS:
        if key not in payload:
            errors.append(f"Missing required field: {key}")

    perf = payload.get("financial_performance", {})
    if not isinstance(perf, dict):
        errors.append("financial_performance must be an object")
    else:
        if "narrative" not in perf:
            errors.append("financial_performance.narrative is required")
        if "table" not in perf:
            errors.append("financial_performance.table is required")
        table = perf.get("table", {})
        if table and not isinstance(table, dict):
            errors.append("financial_performance.table must be an object")
        elif isinstance(table, dict):
            if "headers" not in table or not isinstance(table.get("headers"), list):
                errors.append("financial_performance.table.headers must be a list")
            if "rows" not in table or not isinstance(table.get("rows"), list):
                errors.append("financial_performance.table.rows must be a list")

    if "risk_flags" in payload and not isinstance(payload.get("risk_flags"), list):
        errors.append("risk_flags must be a list")
    if "supporting_evidence" in payload and not isinstance(payload.get("supporting_evidence"), list):
        errors.append("supporting_evidence must be a list")

    return len(errors) == 0, errors

