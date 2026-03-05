"""Synthetic bank behavior generator for missing bank datasets."""

from __future__ import annotations

import random

import pandas as pd

from src.utils.text_processing import slugify


def generate_synthetic_bank(
    company: str,
    revenue: float,
    ebitda: float = 0.0,
    sector_risk: str = "moderate",
    months: int = 24,
) -> tuple[pd.DataFrame, dict]:
    """Create realistic synthetic monthly banking behavior and derived metrics."""
    rng = random.Random(abs(hash((slugify(company), "synthetic_bank_v2"))) % (2**32))
    baseline = max(20.0, float(revenue) / 12.0 if revenue else 60.0)
    margin = (float(ebitda) / float(revenue)) if revenue else 0.12
    risk_factor = 1.0
    sr = (sector_risk or "").lower()
    if "high" in sr:
        risk_factor = 1.18
    elif "low" in sr:
        risk_factor = 0.9

    rows = []
    for m in range(1, months + 1):
        seasonal = 1 + 0.1 * ((m % 6) - 2)
        inflow = max(5.0, baseline * seasonal * rng.uniform(0.82, 1.25))
        outflow_ratio = rng.uniform(0.76, 1.10) * risk_factor * (1.04 if margin < 0.1 else 0.98)
        outflow = inflow * outflow_ratio
        balance = max(2.0, inflow * rng.uniform(0.16, 0.68) / risk_factor)
        rows.append(
            {
                "month_index": m,
                "monthly_inflow": round(inflow, 2),
                "monthly_outflow": round(outflow, 2),
                "average_balance": round(balance, 2),
                "cheque_bounce_count": rng.randint(0, 5 if risk_factor > 1.1 else 3),
            }
        )

    df = pd.DataFrame(rows)
    net = df["monthly_inflow"] - df["monthly_outflow"]
    volatility = float(net.std(ddof=0) / (abs(net.mean()) + 1e-6))
    avg_balance_ratio = float(df["average_balance"].mean() / (df["monthly_outflow"].mean() + 1e-6))

    metrics = {
        "cashflow_volatility": round(volatility, 4),
        "average_balance_ratio": round(avg_balance_ratio, 4),
    }
    return df, metrics
