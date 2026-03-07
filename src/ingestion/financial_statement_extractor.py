"""Multi-year financial statement extraction from annual reports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.cache.financial_cache import FinancialCache
from src.ingestion.financial_extractor import extract_financials_from_text
from src.ingestion.metric_mapper import extract_table_metrics_from_text
from src.ingestion.pdf_parser import extract_pdf_text
from src.validation.unit_normalizer import detect_unit_with_context, normalize_to_crore


def _extract_year(path: Path, text: str) -> str:
    stem = path.stem.lower()
    m = re.search(r"(20\d{2})", stem)
    if m:
        return f"FY{m.group(1)[2:]}"
    m2 = re.search(r"(20\d{2})", text[:2000])
    if m2:
        return f"FY{m2.group(1)[2:]}"
    return "FY00"


def _normalize_financial_row(values: dict[str, Any], unit: str, uncertain: bool = False) -> dict[str, Any]:
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
        "finance_cost",
        "current_assets",
        "current_liabilities",
    ]:
        row[k] = normalize_to_crore(row.get(k), unit, uncertain=uncertain)
    row["unit"] = "INR Crores"
    return row


def _prev_year(fy: str) -> str:
    m = re.search(r"FY(\d{2})", fy)
    if not m:
        return "FY00"
    y = int(m.group(1)) - 1
    return f"FY{y:02d}"


def extract_financial_history(annual_report_dir: Path, cache: FinancialCache) -> tuple[dict, list[dict], list[dict]]:
    """Extract year-wise financial metrics from annual report PDFs."""
    yearly_map: dict[str, dict[str, Any]] = {}
    docs: list[dict[str, Any]] = []
    unit_debug: list[dict[str, Any]] = []
    for pdf in sorted(annual_report_dir.glob("*.pdf")):
        cached = cache.get(pdf)
        if cached is None:
            text = extract_pdf_text(pdf)
            fallback_metrics = extract_financials_from_text(text)
            table_metrics = extract_table_metrics_from_text(text)
            unit_info = detect_unit_with_context(text)
            # Prefer table-extracted current-year values; fallback to prose extractor.
            cur_metrics = dict(fallback_metrics)
            cur_metrics.update(table_metrics.get("current", {}))
            prev_metrics = table_metrics.get("previous", {})
            payload = {
                "source": str(pdf),
                "year": _extract_year(pdf, text),
                "metrics": cur_metrics,
                "metrics_previous": prev_metrics,
                "source_rows": table_metrics.get("source_rows", {}),
                "mapping_confidence": table_metrics.get("confidence", {}),
                "unit_detected": unit_info.get("unit", "crore"),
                "unit_confidence": unit_info.get("confidence", 0.5),
                "unit_evidence": unit_info.get("evidence", ""),
                "unit_uncertain": unit_info.get("uncertain", True),
                "text": text,
            }
            cache.set(pdf, payload)
            docs.append({"source": str(pdf), "text": text})
            cached = payload
        else:
            docs.append({"source": str(pdf), "text": cached.get("text", "")})

        year = str(cached.get("year", "FY00"))
        prev_year = _prev_year(year)

        row = _normalize_financial_row(cached.get("metrics", {}), str(cached.get("unit_detected", "crore")), bool(cached.get("unit_uncertain", True)))
        row["year"] = year
        row["source"] = cached.get("source", str(pdf))
        row["source_rows"] = cached.get("source_rows", {})
        row["mapping_confidence"] = cached.get("mapping_confidence", {})
        row["unit_confidence"] = cached.get("unit_confidence", 0.5)
        row["unit_uncertain"] = cached.get("unit_uncertain", True)

        prev_row = _normalize_financial_row(cached.get("metrics_previous", {}), str(cached.get("unit_detected", "crore")), bool(cached.get("unit_uncertain", True)))
        prev_row["year"] = prev_year
        prev_row["source"] = cached.get("source", str(pdf))
        prev_row["source_rows"] = cached.get("source_rows", {})
        prev_row["mapping_confidence"] = cached.get("mapping_confidence", {})
        prev_row["unit_confidence"] = cached.get("unit_confidence", 0.5)
        prev_row["unit_uncertain"] = cached.get("unit_uncertain", True)

        if year not in yearly_map:
            yearly_map[year] = row
        else:
            for k, v in row.items():
                if yearly_map[year].get(k) is None and v is not None:
                    yearly_map[year][k] = v

        if any(v is not None for k, v in prev_row.items() if k in {"revenue", "ebitda", "net_profit", "debt", "total_assets", "total_liabilities"}):
            if prev_year not in yearly_map:
                yearly_map[prev_year] = prev_row
            else:
                for k, v in prev_row.items():
                    if yearly_map[prev_year].get(k) is None and v is not None:
                        yearly_map[prev_year][k] = v

        unit_debug.append(
            {
                "source": cached.get("source", str(pdf)),
                "year": year,
                "unit": cached.get("unit_detected", "crore"),
                "confidence": cached.get("unit_confidence", 0.5),
                "evidence": cached.get("unit_evidence", ""),
                "uncertain": cached.get("unit_uncertain", True),
            }
        )

    yearly_data = sorted(yearly_map.values(), key=lambda x: x.get("year", ""))
    years = [str(r.get("year")) for r in yearly_data]
    history = {"years": years, "yearly_data": yearly_data, "normalized_unit": "INR Crores"}
    for metric in [
        "revenue",
        "ebitda",
        "net_profit",
        "total_assets",
        "total_liabilities",
        "debt",
        "finance_cost",
        "cash_flow",
        "working_capital",
        "current_assets",
        "current_liabilities",
    ]:
        history[metric] = [r.get(metric) for r in yearly_data]
    return history, docs, unit_debug
