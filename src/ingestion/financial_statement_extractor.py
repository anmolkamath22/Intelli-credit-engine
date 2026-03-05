"""Multi-year financial statement extraction from annual reports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.cache.financial_cache import FinancialCache
from src.ingestion.financial_extractor import extract_financials_from_text
from src.ingestion.pdf_parser import extract_pdf_text
from src.validation.unit_normalizer import detect_unit_from_text, normalize_to_crore


def _extract_year(path: Path, text: str) -> str:
    stem = path.stem.lower()
    m = re.search(r"(20\d{2})", stem)
    if m:
        return f"FY{m.group(1)[2:]}"
    m2 = re.search(r"(20\d{2})", text[:2000])
    if m2:
        return f"FY{m2.group(1)[2:]}"
    return "FY00"


def _normalize_financial_row(values: dict[str, Any], unit: str) -> dict[str, Any]:
    row = dict(values)
    for k in [
        "revenue",
        "ebitda",
        "net_profit",
        "total_assets",
        "total_liabilities",
        "debt",
        "cash_flow",
        "working_capital",
    ]:
        row[k] = normalize_to_crore(row.get(k), unit)
    row["unit"] = "INR Crores"
    return row


def extract_financial_history(annual_report_dir: Path, cache: FinancialCache) -> tuple[dict, list[dict]]:
    """Extract year-wise financial metrics from annual report PDFs."""
    yearly_data: list[dict[str, Any]] = []
    docs: list[dict[str, Any]] = []
    for pdf in sorted(annual_report_dir.glob("*.pdf")):
        cached = cache.get(pdf)
        if cached is None:
            text = extract_pdf_text(pdf)
            metrics = extract_financials_from_text(text)
            unit = detect_unit_from_text(text)
            payload = {
                "source": str(pdf),
                "year": _extract_year(pdf, text),
                "metrics": metrics,
                "unit_detected": unit,
                "text": text,
            }
            cache.set(pdf, payload)
            docs.append({"source": str(pdf), "text": text})
            cached = payload
        else:
            docs.append({"source": str(pdf), "text": cached.get("text", "")})

        row = _normalize_financial_row(cached.get("metrics", {}), str(cached.get("unit_detected", "crore")))
        row["year"] = cached.get("year", "FY00")
        row["source"] = cached.get("source", str(pdf))
        yearly_data.append(row)

    yearly_data = sorted(yearly_data, key=lambda x: x.get("year", ""))
    years = [str(r.get("year")) for r in yearly_data]
    history = {"years": years, "yearly_data": yearly_data, "normalized_unit": "INR Crores"}
    for metric in [
        "revenue",
        "ebitda",
        "net_profit",
        "total_assets",
        "total_liabilities",
        "debt",
        "cash_flow",
        "working_capital",
    ]:
        history[metric] = [r.get(metric) for r in yearly_data]
    return history, docs

