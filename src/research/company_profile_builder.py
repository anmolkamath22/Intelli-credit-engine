"""Builds company overview profile from ingested data."""

from __future__ import annotations


def build_company_overview(financials: dict, company_name: str) -> dict:
    """Construct concise company profile block."""
    return {
        "company_name": company_name,
        "revenue": financials.get("revenue"),
        "net_profit": financials.get("net_profit"),
        "debt": financials.get("debt"),
        "total_assets": financials.get("total_assets"),
        "document_count": financials.get("document_count", 0),
    }
