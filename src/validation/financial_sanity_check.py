"""Sanity checks and corrective normalization for financial history."""

from __future__ import annotations

from copy import deepcopy


NUMERIC_SERIES = [
    "revenue",
    "ebitda",
    "net_profit",
    "total_assets",
    "total_liabilities",
    "debt",
    "cash_flow",
    "working_capital",
]


def _scale_year(record: dict, factor: float) -> dict:
    out = dict(record)
    for k in NUMERIC_SERIES:
        v = out.get(k)
        if v is not None:
            out[k] = float(v) * factor
    return out


def _is_unrealistic(record: dict, prev_record: dict | None = None) -> list[str]:
    issues: list[str] = []
    rev = float(record.get("revenue") or 0.0)
    ebt = float(record.get("ebitda") or 0.0)
    pat = float(record.get("net_profit") or 0.0)
    debt = float(record.get("debt") or 0.0)
    if rev > 0 and ebt > rev:
        issues.append("ebitda_gt_revenue")
    if rev > 0 and pat > rev:
        issues.append("profit_margin_gt_100")
    if debt < 0:
        issues.append("debt_negative")
    if prev_record:
        prev_rev = float(prev_record.get("revenue") or 0.0)
        if prev_rev > 0 and rev < prev_rev * 0.2:
            issues.append("revenue_drop_gt_80")
    return issues


def validate_and_correct_history(history: dict) -> tuple[dict, list[dict]]:
    """Validate financial history and apply simple scaling correction when needed."""
    years = list(history.get("years", []))
    rows = deepcopy(history.get("yearly_data", []))
    anomalies: list[dict] = []
    corrected: list[dict] = []

    for i, row in enumerate(rows):
        prev = corrected[i - 1] if i > 0 else None
        issues = _is_unrealistic(row, prev)
        best = dict(row)
        if issues:
            # Try down-scaling if values are likely in higher unit than detected.
            for factor in (0.1, 0.01, 0.001):
                candidate = _scale_year(row, factor)
                if not _is_unrealistic(candidate, prev):
                    best = candidate
                    break
            anomalies.append({"year": row.get("year"), "issues": issues})

        # Ratio-level correction for noisy extraction rows.
        rev = float(best.get("revenue") or 0.0)
        if rev > 0:
            if float(best.get("ebitda") or 0.0) > rev:
                best["ebitda"] = round(rev * 0.22, 4)
            if float(best.get("net_profit") or 0.0) > rev:
                best["net_profit"] = round(rev * 0.10, 4)
        if float(best.get("debt") or 0.0) < 0:
            best["debt"] = abs(float(best.get("debt") or 0.0))

        if prev:
            prev_rev = float(prev.get("revenue") or 0.0)
            cur_rev = float(best.get("revenue") or 0.0)
            if prev_rev > 0:
                if cur_rev < prev_rev * 0.2:
                    best["revenue"] = round(prev_rev * 0.7, 4)
                elif cur_rev > prev_rev * 5:
                    scaled = cur_rev
                    while scaled > prev_rev * 5:
                        scaled *= 0.1
                    best["revenue"] = round(max(scaled, prev_rev * 0.7), 4)

        corrected.append(best)

    out = {"years": years, "yearly_data": corrected}
    for metric in NUMERIC_SERIES:
        out[metric] = [r.get(metric) for r in corrected]
    out["data_quality_issues"] = anomalies
    return out, anomalies
