"""Circular-trading and revenue-inflation signal detector."""

from __future__ import annotations

import pandas as pd


def detect_circular_trading(gst_sales: float, bank_df: pd.DataFrame | None) -> dict:
    """Detect GST-bank mismatch and rapid in-out patterns."""
    bank_inflow = 0.0
    if bank_df is not None and not bank_df.empty and "monthly_inflow" in bank_df.columns:
        bank_inflow = float(bank_df["monthly_inflow"].astype(float).sum())

    mismatch_ratio = (abs(float(gst_sales) - bank_inflow) / max(float(gst_sales), 1e-6)) if gst_sales > 0 else 0.0
    revenue_inflation_flag = int(gst_sales > 0 and bank_inflow > 0 and (gst_sales > bank_inflow * 1.5 or mismatch_ratio > 0.35))

    circular_trading_flag = 0
    loop_ratio = 0.0
    if bank_df is not None and not bank_df.empty and {"monthly_inflow", "monthly_outflow"}.issubset(bank_df.columns):
        inflow = bank_df["monthly_inflow"].astype(float)
        outflow = bank_df["monthly_outflow"].astype(float)
        ratio = (abs(inflow - outflow) / (inflow + 1e-6)).mean()
        loop_ratio = float((inflow.diff().abs().fillna(0) < inflow.mean() * 0.05).mean())
        if ratio < 0.12 or loop_ratio > 0.6:  # mirrored or repetitive cash movement
            circular_trading_flag = 1

    return {
        "bank_inflow_total": round(bank_inflow, 2),
        "gst_bank_mismatch_ratio": round(float(mismatch_ratio), 4),
        "cashflow_loop_ratio": round(float(loop_ratio), 4),
        "circular_trading_flag": int(circular_trading_flag),
        "revenue_inflation_flag": int(revenue_inflation_flag),
    }
