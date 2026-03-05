"""Primary data ingestor for unified input datasets with synthetic fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.cache.financial_cache import FinancialCache
from src.ingestion.financial_extractor import extract_financials_from_text, merge_financial_dicts
from src.ingestion.financial_statement_extractor import extract_financial_history
from src.ingestion.pdf_parser import extract_pdf_text
from src.synthetic.bank_generator import generate_synthetic_bank
from src.synthetic.gst_generator import generate_synthetic_gst
from src.utils.file_loader import list_files, read_csv, read_json
from src.utils.text_processing import clean_text, slugify
from src.validation.financial_sanity_check import validate_and_correct_history
from src.validation.unit_normalizer import detect_unit_from_text, normalize_to_crore


class DataIngestor:
    """Ingest local company datasets and produce complete processed artifacts."""

    def __init__(self, input_root: Path, processed_root: Path, legacy_root: Path | None = None) -> None:
        self.input_root = input_root
        self.processed_root = processed_root
        self.legacy_root = legacy_root

    def _company_input_dir(self, company: str) -> Path:
        slug = slugify(company)
        primary = self.input_root / slug
        if primary.exists():
            return primary
        if self.legacy_root and (self.legacy_root / slug).exists():
            return self.legacy_root / slug
        return primary

    @staticmethod
    def _read_dir_text_files(directory: Path, exts: set[str]) -> list[dict]:
        docs = []
        for p in list_files(directory, exts=exts):
            try:
                docs.append({"source": str(p), "text": clean_text(p.read_text(encoding="utf-8", errors="ignore"))})
            except Exception:
                continue
        return docs

    def ingest_company(self, company: str, sector: str | None = None) -> dict:
        """Ingest local files; generate synthetic signals where datasets are missing."""
        slug = slugify(company)
        cdir = self._company_input_dir(company)
        out_dir = self.processed_root / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        subdirs = {
            "annual_reports": cdir / "annual_reports",
            "financial_statements": cdir / "financial_statements",
            "balance_sheets": cdir / "balance_sheets",
            "gst_returns": cdir / "gst_returns",
            "bank_statements": cdir / "bank_statements",
            "legal_documents": cdir / "legal_documents",
            "news_documents": cdir / "news_documents",
        }

        dataset_presence = {k: int(v.exists() and any(v.rglob('*'))) for k, v in subdirs.items()}

        doc_texts: list[dict] = []
        extracted_financial_parts: list[dict[str, Any]] = []
        financial_history = {"years": [], "yearly_data": [], "normalized_unit": "INR Crores"}

        # Multi-year annual report extraction with cache.
        cache = FinancialCache(out_dir / "cache" / "financial_cache.json")
        if subdirs["annual_reports"].exists():
            annual_history, annual_docs = extract_financial_history(subdirs["annual_reports"], cache)
            financial_history = annual_history
            for d in annual_docs:
                if d.get("text"):
                    doc_texts.append({"source": d["source"], "text": clean_text(d["text"])})
            extracted_financial_parts.extend(annual_history.get("yearly_data", []))
        cache.save()

        for key in ["financial_statements", "balance_sheets"]:
            d = subdirs[key]
            pdfs = list_files(d, exts={".pdf"})
            jsons = list_files(d, exts={".json"})
            csvs = list_files(d, exts={".csv"})

            for pdf in pdfs:
                text = extract_pdf_text(pdf)
                if text:
                    ctext = clean_text(text)
                    doc_texts.append({"source": str(pdf), "text": ctext})
                    unit = detect_unit_from_text(text)
                    metrics = extract_financials_from_text(ctext)
                    for mk in [
                        "revenue",
                        "net_profit",
                        "debt",
                        "total_assets",
                        "total_liabilities",
                        "cash_flow",
                        "ebitda",
                        "working_capital",
                    ]:
                        metrics[mk] = normalize_to_crore(metrics.get(mk), unit)
                    extracted_financial_parts.append(metrics)

            for jf in jsons:
                payload = read_json(jf)
                if payload:
                    doc_texts.append({"source": str(jf), "text": clean_text(json.dumps(payload))})
                    extracted_financial_parts.append({
                        "revenue": payload.get("revenue") or payload.get("total_income"),
                        "net_profit": payload.get("net_profit") or payload.get("pat"),
                        "debt": payload.get("debt") or payload.get("borrowings"),
                        "total_assets": payload.get("total_assets"),
                        "total_liabilities": payload.get("total_liabilities"),
                        "cash_flow": payload.get("cash_flow") or payload.get("cash_flow_from_operations"),
                        "ebitda": payload.get("ebitda"),
                        "working_capital": payload.get("working_capital"),
                        "auditor_remarks": payload.get("auditor_remarks", []),
                    })

            for cf in csvs:
                try:
                    df = read_csv(cf)
                    doc_texts.append({"source": str(cf), "text": clean_text(df.head(400).to_csv(index=False))})
                    if not df.empty:
                        row = df.iloc[0].to_dict()
                        extracted_financial_parts.append({
                            "revenue": row.get("revenue") or row.get("total_income"),
                            "net_profit": row.get("net_profit") or row.get("pat"),
                            "debt": row.get("debt"),
                            "total_assets": row.get("total_assets"),
                            "total_liabilities": row.get("total_liabilities"),
                            "cash_flow": row.get("cash_flow"),
                            "ebitda": row.get("ebitda"),
                            "working_capital": row.get("working_capital"),
                            "auditor_remarks": [],
                        })
                except Exception:
                    continue

        # Validate/correct yearly history and anchor current financials on latest year.
        if not financial_history.get("yearly_data"):
            # Fallback history from whatever financial data was extracted.
            fallback = merge_financial_dicts(extracted_financial_parts)
            financial_history = {
                "years": ["FY24"],
                "yearly_data": [{**fallback, "year": "FY24", "unit": "INR Crores"}],
                "normalized_unit": "INR Crores",
            }
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
                financial_history[metric] = [financial_history["yearly_data"][0].get(metric)]

        financial_history, dq_issues = validate_and_correct_history(financial_history)
        latest = financial_history["yearly_data"][-1] if financial_history["yearly_data"] else {}
        prev = financial_history["yearly_data"][-2] if len(financial_history["yearly_data"]) > 1 else {}

        financials = merge_financial_dicts(extracted_financial_parts + [latest])
        financials["company_name"] = company
        financials["company_slug"] = slug
        financials["document_count"] = len(doc_texts)
        financials["normalized_unit"] = "INR Crores"
        for k in [
            "revenue",
            "net_profit",
            "debt",
            "total_assets",
            "total_liabilities",
            "cash_flow",
            "ebitda",
            "working_capital",
        ]:
            if latest.get(k) is not None:
                financials[k] = latest.get(k)
        financials["revenue_prev"] = prev.get("revenue")
        financials["data_quality_issues"] = dq_issues

        revenue_for_synth = float(financials.get("revenue") or 500.0)
        ebitda_for_synth = float(financials.get("ebitda") or 50.0)

        # GST ingestion + synthetic fallback
        gst_payload: dict[str, Any] = {}
        gst_jsons = list_files(subdirs["gst_returns"], exts={".json"})
        gst_csvs = list_files(subdirs["gst_returns"], exts={".csv"})
        for p in gst_jsons:
            gst_payload.update(read_json(p))
        if not gst_payload and gst_csvs:
            try:
                df = read_csv(gst_csvs[0])
                gst_payload = {"uploaded_rows": df.to_dict(orient="records")[:200]}
            except Exception:
                pass

        gst_synthetic = {}
        if not gst_payload:
            gst_synthetic = generate_synthetic_gst(revenue_for_synth, ebitda=ebitda_for_synth, sector=sector)
            gst_payload = dict(gst_synthetic)
            gst_payload["synthetic_generated"] = True
        else:
            gst_payload["synthetic_generated"] = False

        # Bank ingestion + synthetic fallback
        bank_df = None
        bank_csvs = list_files(subdirs["bank_statements"], exts={".csv"})
        if bank_csvs:
            try:
                bank_df = read_csv(bank_csvs[0])
            except Exception:
                bank_df = None

        bank_synthetic_features = {}
        bank_synthetic_generated = False
        if bank_df is None or bank_df.empty:
            bank_df, bank_synthetic_features = generate_synthetic_bank(
                company,
                revenue_for_synth,
                ebitda=ebitda_for_synth,
                sector_risk=str(sector or "moderate"),
                months=24,
            )
            bank_synthetic_generated = True

        (out_dir / "company_financials.json").write_text(json.dumps(financials, indent=2, ensure_ascii=True), encoding="utf-8")
        (out_dir / "financial_features.json").write_text(json.dumps(financials, indent=2, ensure_ascii=True), encoding="utf-8")
        (out_dir / "financial_history.json").write_text(
            json.dumps(financial_history, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        (out_dir / "documents.json").write_text(json.dumps(doc_texts, indent=2, ensure_ascii=True), encoding="utf-8")
        (out_dir / "synthetic_gst_features.json").write_text(json.dumps(gst_payload, indent=2, ensure_ascii=True), encoding="utf-8")

        bank_df.to_csv(out_dir / "synthetic_bank_features.csv", index=False)
        bank_payload = {
            "synthetic_generated": bank_synthetic_generated,
            **(bank_synthetic_features if bank_synthetic_generated else {}),
        }
        (out_dir / "synthetic_bank_features.json").write_text(json.dumps(bank_payload, indent=2, ensure_ascii=True), encoding="utf-8")

        return {
            "financials": financials,
            "gst_signals": gst_payload,
            "bank_df": bank_df,
            "bank_synthetic_generated": bank_synthetic_generated,
            "documents": doc_texts,
            "company_dir": cdir,
            "processed_dir": out_dir,
            "dataset_presence": dataset_presence,
            "financial_history": financial_history,
        }
