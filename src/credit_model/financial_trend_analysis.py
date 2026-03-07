"""Multi-year financial trend analysis."""

from __future__ import annotations


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _cagr(first: float, last: float, periods: int) -> float:
    if first <= 0 or last <= 0 or periods <= 0:
        return 0.0
    return (last / first) ** (1 / periods) - 1


def _safe_cagr(first: float, last: float, periods: int) -> tuple[float | None, str | None]:
    if periods <= 0:
        return None, "insufficient_periods"
    if first <= 0 or last <= 0:
        return None, "non_positive_base_or_terminal"
    if first < 1.0:
        return None, "base_near_zero"
    return _cagr(first, last, periods), None


def compute_financial_trends(history: dict) -> dict:
    """Compute key trend metrics over available history (up to 5 years)."""
    rows = history.get("yearly_data", [])
    if len(rows) < 2:
        return {
            "revenue_cagr_5y": 0.0,
            "ebitda_cagr_5y": 0.0,
            "net_profit_cagr_5y": 0.0,
            "debt_reduction_rate": 0.0,
            "ebitda_margin_first": 0.0,
            "ebitda_margin_last": 0.0,
            "ebitda_margin_trend": "stable",
            "interest_coverage_first": 0.0,
            "interest_coverage_last": 0.0,
            "interest_coverage_trend": "stable",
        }

    first, last = rows[0], rows[-1]
    periods = len(rows) - 1

    rev_first = float(first.get("revenue") or 0.0)
    rev_last = float(last.get("revenue") or 0.0)
    ebitda_first = float(first.get("ebitda") or 0.0)
    ebitda_last = float(last.get("ebitda") or 0.0)
    pat_first = float(first.get("net_profit") or 0.0)
    pat_last = float(last.get("net_profit") or 0.0)
    debt_first = float(first.get("debt") or 0.0)
    debt_last = float(last.get("debt") or 0.0)

    ebitda_margin_first = _safe_div(ebitda_first, rev_first)
    ebitda_margin_last = _safe_div(ebitda_last, rev_last)

    ic_first = _safe_div(ebitda_first, max(1e-6, debt_first * 0.09))
    ic_last = _safe_div(ebitda_last, max(1e-6, debt_last * 0.09))

    rev_cagr, rev_reason = _safe_cagr(rev_first, rev_last, periods)
    ebitda_cagr, ebitda_reason = _safe_cagr(ebitda_first, ebitda_last, periods)
    pat_cagr, pat_reason = _safe_cagr(pat_first, pat_last, periods)

    debt_change_rate = _safe_div(debt_last - debt_first, debt_first) if debt_first > 0 else 0.0
    debt_trend = "increasing" if debt_last > debt_first else "decreasing" if debt_last < debt_first else "stable"

    return {
        "revenue_cagr_5y": round(float(rev_cagr or 0.0), 6),
        "revenue_cagr_valid": rev_cagr is not None,
        "revenue_cagr_reason": rev_reason,
        "ebitda_cagr_5y": round(float(ebitda_cagr or 0.0), 6),
        "ebitda_cagr_valid": ebitda_cagr is not None,
        "ebitda_cagr_reason": ebitda_reason,
        "net_profit_cagr_5y": round(float(pat_cagr or 0.0), 6),
        "net_profit_cagr_valid": pat_cagr is not None,
        "net_profit_cagr_reason": pat_reason,
        "debt_change_rate": round(float(debt_change_rate), 6),
        "debt_trend": debt_trend,
        "debt_start": round(debt_first, 4),
        "debt_end": round(debt_last, 4),
        "ebitda_margin_first": round(ebitda_margin_first, 6),
        "ebitda_margin_last": round(ebitda_margin_last, 6),
        "ebitda_margin_trend": "improving" if ebitda_margin_last > ebitda_margin_first else "weakening",
        "interest_coverage_first": round(ic_first, 6),
        "interest_coverage_last": round(ic_last, 6),
        "interest_coverage_trend": "improving" if ic_last > ic_first else "weakening",
    }
