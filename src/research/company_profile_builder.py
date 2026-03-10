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


def build_company_profile(
    company_name: str,
    entity_profile: dict,
    financials: dict,
    board_of_directors: list[str],
    promoter_summary: str,
    research_summary: dict,
    litigation_summary: dict,
    officer_inputs: dict,
) -> dict:
    """Canonical reusable company profile object used across UI/scoring/report/RAG."""
    return {
        "company_name": company_name,
        "CIN": entity_profile.get("cin", ""),
        "PAN": entity_profile.get("pan", ""),
        "sector": entity_profile.get("sector", ""),
        "subsector": entity_profile.get("subsector", ""),
        "turnover": entity_profile.get("turnover", financials.get("revenue")),
        "board_of_directors": board_of_directors,
        "promoter_summary": promoter_summary,
        "company_summary": (
            f"Revenue INR {float(financials.get('revenue') or 0.0):,.2f} Cr, "
            f"EBITDA INR {float(financials.get('ebitda') or 0.0):,.2f} Cr, "
            f"debt INR {float(financials.get('debt') or 0.0):,.2f} Cr."
        ),
        "research_risk_summary": {
            "news_risk_assessment": research_summary.get("news_risk_assessment", "unknown_insufficient_data"),
            "research_confidence": research_summary.get("research_confidence", "low"),
            "sector_risk": research_summary.get("sector_risk", "unknown"),
            "board_risk": research_summary.get("board_risk"),
            "promoter_risk": research_summary.get("promoter_risk"),
        },
        "legal_risk_summary": {
            "litigation_count": litigation_summary.get("litigation_count"),
            "litigation_risk_score": litigation_summary.get("litigation_risk_score"),
            "litigation_risk_status": litigation_summary.get("litigation_risk_status", "unknown_insufficient_public_evidence"),
            "litigation_confidence": litigation_summary.get("litigation_confidence", "low"),
            "insolvency_flag": litigation_summary.get("insolvency_flag"),
        },
        "management_risk_summary": {
            "officer_management_credibility": officer_inputs.get("management_credibility"),
            "officer_supply_chain_risk": officer_inputs.get("supply_chain_risk"),
            "officer_inventory_build_up": officer_inputs.get("inventory_build_up"),
        },
    }
