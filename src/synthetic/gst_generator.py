"""Synthetic GST signal generator for missing GST datasets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GSTSynthetic:
    """Synthetic GST outputs."""

    gst_sales_estimate: float
    gst_tax_paid_estimate: float
    gst_filing_delay: int
    gst_compliance_score: float


def generate_synthetic_gst(revenue: float, ebitda: float = 0.0, sector: str | None = None) -> dict:
    """Generate synthetic GST metrics when uploaded GST data is unavailable."""
    sector_rates = {
        "technology": 0.18,
        "it": 0.18,
        "building materials / pipes": 0.18,
        "air-conditioning / engineering": 0.18,
        "electrical cables / infrastructure": 0.18,
        "apparel / consumer goods": 0.12,
        "auto": 0.28,
        "logistics": 0.18,
    }
    s = (sector or "").strip().lower()
    rate = sector_rates.get(s, 0.18)

    margin = (float(ebitda) / float(revenue)) if revenue else 0.12
    margin_adj = max(0.85, min(1.02, 1 - max(0.0, margin - 0.2)))
    gst_sales = max(0.0, float(revenue) * 0.92 * margin_adj)
    gst_tax = gst_sales * rate

    # deterministic proxy behavior from revenue scale and margin quality
    delay = int(min(65, max(3, 36 - (revenue / 400.0) + (0.18 - min(0.18, margin)) * 30)))
    compliance = max(0.0, min(100.0, 100 - delay * 1.2))

    out = GSTSynthetic(
        gst_sales_estimate=round(gst_sales, 2),
        gst_tax_paid_estimate=round(gst_tax, 2),
        gst_filing_delay=delay,
        gst_compliance_score=round(compliance, 2),
    )
    return out.__dict__
