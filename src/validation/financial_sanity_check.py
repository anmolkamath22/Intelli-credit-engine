"""Sanity checks and controlled corrective normalization for financial history."""

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
    """Validate financial history and apply conservative corrections."""
    years = list(history.get("years", []))
    rows = deepcopy(history.get("yearly_data", []))
    anomalies: list[dict] = []
    corrected: list[dict] = []

    for i, row in enumerate(rows):
        prev = corrected[i - 1] if i > 0 else None
        issues = _is_unrealistic(row, prev)
        best = dict(row)
        unreliable_metrics: list[str] = []
        if issues:
            # Try down-scaling if values are likely in higher unit than detected.
            for factor in (0.1, 0.01, 10.0):
                candidate = _scale_year(row, factor)
                if not _is_unrealistic(candidate, prev):
                    best = candidate
                    break
            anomalies.append({"year": row.get("year"), "issues": issues, "action": "scaled_or_flagged"})

        # Controlled ratio correction with explicit reliability flags.
        rev = float(best.get("revenue") or 0.0)
        if rev > 0:
            if float(best.get("ebitda") or 0.0) > rev:
                unreliable_metrics.append("ebitda")
                best["ebitda"] = round(rev * 0.22, 4)
            if float(best.get("net_profit") or 0.0) > rev:
                unreliable_metrics.append("net_profit")
                best["net_profit"] = round(rev * 0.10, 4)
        if float(best.get("debt") or 0.0) < 0:
            unreliable_metrics.append("debt")
            best["debt"] = abs(float(best.get("debt") or 0.0))

        assets = float(best.get("total_assets") or 0.0)
        liabilities = float(best.get("total_liabilities") or 0.0)
        if assets > 0 and liabilities > assets * 1.08:
            unreliable_metrics.append("total_liabilities")
            best["total_liabilities"] = round(assets * 0.92, 4)

        if prev:
            prev_rev = float(prev.get("revenue") or 0.0)
            cur_rev = float(best.get("revenue") or 0.0)
            if prev_rev > 0:
                if cur_rev < prev_rev * 0.2:
                    unreliable_metrics.append("revenue")
                    best["revenue"] = round(prev_rev * 0.7, 4)
                elif cur_rev > prev_rev * 5:
                    unreliable_metrics.append("revenue")
                    scaled = cur_rev
                    while scaled > prev_rev * 5:
                        scaled *= 0.1
                    best["revenue"] = round(max(scaled, prev_rev * 0.7), 4)

        # Margin sanity bounds for downstream ratios.
        rev2 = float(best.get("revenue") or 0.0)
        if rev2 > 0:
            pm = float(best.get("net_profit") or 0.0) / rev2
            em = float(best.get("ebitda") or 0.0) / rev2
            if pm < -1.0 or pm > 1.0:
                unreliable_metrics.append("profit_margin")
            if em < -1.0 or em > 1.0:
                unreliable_metrics.append("ebitda_margin")

        best["unreliable_metrics"] = sorted(set(unreliable_metrics))

        corrected.append(best)

    out = {"years": years, "yearly_data": corrected}
    for metric in NUMERIC_SERIES:
        out[metric] = [r.get(metric) for r in corrected]
    out["data_quality_issues"] = anomalies
    return out, anomalies
