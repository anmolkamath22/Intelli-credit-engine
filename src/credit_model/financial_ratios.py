"""Validated financial ratio engine."""

from __future__ import annotations

from typing import Any


def _safe_ratio(num: float | None, den: float | None, name: str) -> dict[str, Any]:
    if num is None or den is None:
        return {"value": None, "reason": f"{name}: missing numerator/denominator"}
    if abs(den) < 1e-9:
        return {"value": None, "reason": f"{name}: denominator is zero"}
    return {"value": num / den, "reason": None}


def build_validated_financials(history: dict) -> dict[str, Any]:
    """Compute yearly ratios with validation metadata."""
    years = history.get("years", [])
    rows = history.get("yearly_data", [])
    yearly_ratios: list[dict[str, Any]] = []

    for y, r in zip(years, rows):
        revenue = r.get("revenue")
        net_profit = r.get("net_profit")
        ebitda = r.get("ebitda")
        debt = r.get("debt")
        assets = r.get("total_assets")
        liabilities = r.get("total_liabilities")
        current_assets = r.get("current_assets")
        current_liabilities = r.get("current_liabilities")
        finance_cost = r.get("finance_cost")

        equity = None
        if assets is not None and liabilities is not None:
            equity = float(assets) - float(liabilities)

        pm = _safe_ratio(float(net_profit) if net_profit is not None else None, float(revenue) if revenue is not None else None, "profit_margin")
        em = _safe_ratio(float(ebitda) if ebitda is not None else None, float(revenue) if revenue is not None else None, "ebitda_margin")
        de = _safe_ratio(float(debt) if debt is not None else None, equity, "debt_to_equity")
        cr = _safe_ratio(
            float(current_assets) if current_assets is not None else None,
            float(current_liabilities) if current_liabilities is not None else None,
            "current_ratio",
        )
        ic = _safe_ratio(float(ebitda) if ebitda is not None else None, float(finance_cost) if finance_cost is not None else None, "interest_coverage")
        debitda = _safe_ratio(float(debt) if debt is not None else None, float(ebitda) if ebitda is not None else None, "debt_to_ebitda")

        unreliable = set(r.get("unreliable_metrics", []) or [])
        # Suppress absurd ratios when source metrics are flagged unreliable.
        ratio_pack = {
            "profit_margin": pm,
            "ebitda_margin": em,
            "debt_to_equity": de,
            "current_ratio": cr,
            "interest_coverage": ic,
            "debt_to_ebitda": debitda,
        }
        if "revenue" in unreliable or "net_profit" in unreliable:
            ratio_pack["profit_margin"] = {"value": None, "reason": "suppressed: unreliable source metrics"}
        if "revenue" in unreliable or "ebitda" in unreliable:
            ratio_pack["ebitda_margin"] = {"value": None, "reason": "suppressed: unreliable source metrics"}
            ratio_pack["debt_to_ebitda"] = {"value": None, "reason": "suppressed: unreliable source metrics"}
        if "debt" in unreliable or "total_liabilities" in unreliable:
            ratio_pack["debt_to_equity"] = {"value": None, "reason": "suppressed: unreliable source metrics"}

        yearly_ratios.append(
            {
                "year": y,
                "metrics": {
                    "revenue": revenue,
                    "ebitda": ebitda,
                    "net_profit": net_profit,
                    "debt": debt,
                    "finance_cost": finance_cost,
                    "total_assets": assets,
                    "total_liabilities": liabilities,
                },
                "ratios": ratio_pack,
                "unreliable_metrics": sorted(unreliable),
            }
        )

    latest = yearly_ratios[-1] if yearly_ratios else {}
    return {
        "normalized_unit": "INR Crores",
        "years": years,
        "yearly_validated": yearly_ratios,
        "latest_year": latest.get("year"),
        "latest_ratios": latest.get("ratios", {}),
    }

