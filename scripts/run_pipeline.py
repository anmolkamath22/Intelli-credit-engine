"""Unified intelli-credit-engine pipeline runner (upgraded for partial datasets)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from scripts.run_cam_generation import run_cam
from src.analysis.financial_narrative_generator import generate_financial_narrative
from src.credit_model.circular_trading_detector import detect_circular_trading
from src.credit_model.decision_trace import build_decision_trace
from src.credit_model.feature_engineering import build_credit_features
from src.credit_model.financial_ratios import build_validated_financials
from src.credit_model.financial_trend_analysis import compute_financial_trends
from src.credit_model.scoring_model import score_credit
from src.databricks.pipeline import write_databricks_tables
from src.ingestion.data_ingestor import DataIngestor
from src.officer_portal.credit_officer_inputs import load_officer_inputs
from src.research.research_agent import run_research_agent
from src.utils.logger import get_logger
from src.utils.text_processing import slugify, split_words
from src.vector_store.embedding_builder import EmbeddingBuilder
from src.vector_store.retriever import VectorRetriever


def _load_cfg(root: Path) -> dict:
    return yaml.safe_load((root / "configs" / "pipeline_config.yaml").read_text(encoding="utf-8"))


def _source_type(path_or_source: str) -> str:
    s = path_or_source.lower()
    if "annual_reports" in s:
        return "annual_reports"
    if "financial_statements" in s:
        return "financial_statements"
    if "balance_sheets" in s:
        return "balance_sheets"
    if "gst_returns" in s or "synthetic_gst_features" in s:
        return "gst_returns"
    if "bank_statements" in s or "synthetic_bank_features" in s:
        return "bank_statements"
    if "legal_documents" in s or "litigation" in s:
        return "legal_documents"
    if "news_documents" in s:
        return "news_documents"
    if "research_summary" in s:
        return "research_summary"
    if "credit_features" in s or "financial_features" in s or "financial_history" in s:
        return "feature_summary"
    return "other"


def _section_type_from_source(source_type: str) -> str:
    if source_type in {"annual_reports", "financial_statements", "balance_sheets", "feature_summary"}:
        return "financial"
    if source_type in {"legal_documents"}:
        return "litigation"
    if source_type in {"news_documents"}:
        return "industry"
    if source_type in {"research_summary"}:
        return "decision"
    return "general"


def _fiscal_year_from_source(src: str) -> str | None:
    import re

    m = re.search(r"FY(\d{2})", src, flags=re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}"
    return None


def _write_financial_audit(
    root: Path,
    company: str,
    financial_history: dict[str, Any],
    trends: dict[str, Any],
    anomalies: list[dict[str, Any]],
) -> str:
    debug_dir = root / "outputs" / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    suspicious = []
    for row in financial_history.get("yearly_data", []):
        conf = row.get("mapping_confidence", {}) or {}
        weak = [k for k, v in conf.items() if float(v) < 0.45]
        if weak:
            suspicious.append({"year": row.get("year"), "weak_mappings": weak, "source": row.get("source")})
    report = {
        "company": company,
        "root_causes": [
            "prose-first extraction may capture non-statement numbers",
            "unit ambiguity in annual-report pages",
            "limited section-aware retrieval causing generic evidence snippets",
        ],
        "years_affected": [r.get("year") for r in financial_history.get("yearly_data", [])],
        "suspicious_mappings": suspicious,
        "anomalies": anomalies,
        "trend_snapshot": trends,
        "fix_recommendations": [
            "prioritize table row labels and year columns over prose matches",
            "track unit confidence and avoid hard normalization when uncertain",
            "suppress unreliable metrics from ratios and narrative",
            "use section-aware RAG filters by source_type and section_type",
        ],
    }
    out = debug_dir / "financial_audit_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    return str(out)


def _filter_evidence_by_keywords(
    evidence: list[dict[str, Any]],
    keywords: list[str],
    limit: int,
    min_hits: int = 1,
    require_number: bool = False,
    exclude_terms: list[str] | None = None,
) -> list[dict[str, Any]]:
    import re

    ks = [k.lower() for k in keywords]
    ex = [x.lower() for x in (exclude_terms or [])]
    ranked: list[tuple[int, dict[str, Any]]] = []
    for e in evidence:
        txt = str(e.get("chunk", "")).lower()
        if ex and any(x in txt for x in ex):
            continue
        if require_number and not re.search(r"\d", txt):
            continue
        hit = sum(1 for k in ks if k in txt)
        if hit >= min_hits:
            ranked.append((hit, e))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in ranked[:limit]]


def run(company: str, debug_financials: bool = False) -> dict:
    root = Path(__file__).resolve().parents[1]
    cfg = _load_cfg(root)
    logger = get_logger(log_file=str(root / "docs" / "pipeline.log"))

    input_root = root / cfg.get("input_root", "data/input")
    processed_root = root / cfg.get("processed_root", "data/processed")
    output_root = root / cfg.get("output_root", "outputs/cam_reports")
    legacy_root = (root / cfg.get("legacy_dataset_root", "../credit-dataset-builder/datasets")).resolve()

    # Optional sector lookup from company list.
    company_list_path = root / "configs" / "company_list.yaml"
    sector = None
    if company_list_path.exists():
        company_list = yaml.safe_load(company_list_path.read_text(encoding="utf-8")) or {}
        for row in company_list.get("companies", []):
            if str(row.get("name", "")).strip().lower() == company.strip().lower():
                sector = row.get("sector")
                break

    ingestor = DataIngestor(input_root=input_root, processed_root=processed_root, legacy_root=legacy_root)
    ing = ingestor.ingest_company(company, sector=sector)
    slug = slugify(company)

    embedder = EmbeddingBuilder(dim=int(cfg.get("vector", {}).get("embedding_dim", 64)))
    retriever = VectorRetriever(embedder)
    chunk_size = int(cfg.get("vector", {}).get("chunk_size_words", 300))
    overlap = int(cfg.get("vector", {}).get("overlap_words", 50))

    # Index ingested docs and processed signal files for RAG.
    for d in ing["documents"]:
        st = _source_type(d.get("source", ""))
        sec = _section_type_from_source(st)
        fy = _fiscal_year_from_source(d.get("source", ""))
        for chunk in split_words(d.get("text", ""), chunk_size=chunk_size, overlap=overlap):
            retriever.add(
                source=d.get("source", "unknown"),
                chunk=chunk,
                metadata={"source_type": st, "section_type": sec, "fiscal_year": fy, "metric_type": "document"},
            )

    proc_dir = processed_root / slug
    for f in [
        proc_dir / "financial_features.json",
        proc_dir / "financial_history.json",
        proc_dir / "synthetic_gst_features.json",
        proc_dir / "synthetic_bank_features.json",
    ]:
        if f.exists():
            st = _source_type(str(f))
            sec = _section_type_from_source(st)
            text = f.read_text(encoding="utf-8", errors="ignore")
            for chunk in split_words(text, chunk_size=chunk_size, overlap=overlap):
                retriever.add(
                    source=str(f),
                    chunk=chunk,
                    metadata={"source_type": st, "section_type": sec, "fiscal_year": None, "metric_type": "summary"},
                )

    research_out = proc_dir / "research_summary.json"
    research_evidence_out = proc_dir / "research_evidence.json"
    research = run_research_agent(
        company_name=company,
        financials=ing["financials"],
        company_dir=ing["company_dir"],
        retriever=retriever,
        output_path=research_out,
        evidence_output_path=research_evidence_out,
        top_k=int(cfg.get("retrieval", {}).get("top_k", 5)),
    )

    officer_inputs = load_officer_inputs(ing["company_dir"] / "qualitative" / "officer_inputs.json")

    gst_sales = float(ing["gst_signals"].get("gst_sales_estimate") or ing["financials"].get("revenue") or 0.0)
    circular_flags = detect_circular_trading(gst_sales=gst_sales, bank_df=ing["bank_df"])
    financial_trends = compute_financial_trends(ing.get("financial_history", {}))
    trend_narrative = generate_financial_narrative(company, financial_trends, ing.get("financial_history", {}))
    validated_financials = build_validated_financials(ing.get("financial_history", {}))
    (proc_dir / "financial_trends.json").write_text(
        json.dumps(financial_trends, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    (proc_dir / "validated_financials.json").write_text(
        json.dumps(validated_financials, indent=2, ensure_ascii=True), encoding="utf-8"
    )

    features = build_credit_features(
        financials=ing["financials"],
        financial_trends=financial_trends,
        research=research,
        bank_df=ing["bank_df"],
        officer_inputs=officer_inputs,
        gst_signals=ing["gst_signals"],
        circular_flags=circular_flags,
    )

    scoring = score_credit(features, ing["financials"], cfg.get("scoring", {}), research=research)
    trace = build_decision_trace(features, scoring, research.get("supporting_evidence", []), research=research)
    debug_dir = root / "outputs" / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    score_audit_path = debug_dir / f"score_audit_{slug}.json"
    score_audit_path.write_text(
        json.dumps(scoring.get("score_audit", {}), indent=2, ensure_ascii=True), encoding="utf-8"
    )

    (proc_dir / "credit_features.json").write_text(json.dumps(features, indent=2, ensure_ascii=True), encoding="utf-8")
    (proc_dir / "decision_trace.json").write_text(json.dumps(trace, indent=2, ensure_ascii=True), encoding="utf-8")
    (proc_dir / "scoring_output.json").write_text(json.dumps(scoring, indent=2, ensure_ascii=True), encoding="utf-8")

    # Expand vector store with research + scoring artifacts before CAM generation.
    for f in [
        proc_dir / "research_summary.json",
        proc_dir / "research_evidence.json",
        proc_dir / "financial_trends.json",
        proc_dir / "validated_financials.json",
        proc_dir / "credit_features.json",
        proc_dir / "decision_trace.json",
        proc_dir / "scoring_output.json",
    ]:
        if f.exists():
            st = _source_type(str(f))
            sec = _section_type_from_source(st)
            text = f.read_text(encoding="utf-8", errors="ignore")
            for chunk in split_words(text, chunk_size=chunk_size, overlap=overlap):
                retriever.add(
                    source=str(f),
                    chunk=chunk,
                    metadata={"source_type": st, "section_type": sec, "fiscal_year": None, "metric_type": "summary"},
                )

    fin_candidates = retriever.query(
            "audited financial statement revenue ebitda debt finance cost operating cash flow",
            top_k=20,
            source_types=["annual_reports", "financial_statements", "balance_sheets", "feature_summary"],
            section_type="financial",
        )
    fin_evidence = _filter_evidence_by_keywords(
        fin_candidates,
        ["revenue", "ebitda", "profit", "borrowings", "debt", "assets", "liabilities", "cash flow", "finance cost"],
        6,
        min_hits=2,
        require_number=True,
        exclude_terms=["board meeting", "director", "human capital", "esg", "product launch", "patent"],
    )
    if not fin_evidence:
        fin_evidence = fin_candidates[:4]
    legal_candidates = retriever.query(
            "litigation legal dispute insolvency tribunal case",
            top_k=20,
            source_types=["legal_documents", "annual_reports"],
            section_type="litigation",
        )
    legal_evidence = _filter_evidence_by_keywords(
        legal_candidates,
        ["litigation", "case", "petition", "tribunal", "insolvency", "legal", "nclt"],
        4,
        min_hits=1,
    )
    if not legal_evidence:
        legal_evidence = legal_candidates[:3]
    industry_candidates = retriever.query(
            "sector headwinds demand slowdown policy risk",
            top_k=20,
            source_types=["news_documents", "annual_reports"],
            section_type="industry",
        )
    industry_evidence = _filter_evidence_by_keywords(
        industry_candidates,
        ["sector", "demand", "policy", "headwind", "market", "slowdown", "commodity"],
        3,
        min_hits=1,
        exclude_terms=["director", "board meeting"],
    )
    if not industry_evidence:
        industry_evidence = industry_candidates[:2]
    decision_candidates = retriever.query(
            "decision rationale recommendation risk premium loan limit",
            top_k=15,
            source_types=["feature_summary", "annual_reports"],
            section_type="decision",
        )
    decision_evidence = _filter_evidence_by_keywords(
        decision_candidates,
        ["loan", "risk", "debt", "coverage", "profit", "cash flow", "limit", "interest"],
        3,
        min_hits=2,
        require_number=True,
    )
    if not decision_evidence:
        decision_evidence = decision_candidates[:2]
    cam_evidence = fin_evidence + legal_evidence + industry_evidence + decision_evidence

    cam_result = run_cam(
        company=company,
        payload={
            "slug": slug,
            "financials": ing["financials"],
            "financial_history": ing.get("financial_history", {}),
            "financial_trends": financial_trends,
            "trend_narrative": trend_narrative,
            "validated_financials": validated_financials,
            "dataset_presence": ing.get("dataset_presence", {}),
            "cam_evidence": cam_evidence,
            "research": research,
            "features": features,
            "scoring": scoring,
            "trace": trace,
        },
        output_dir=output_root,
    )

    # Run-level aliases under outputs/cam_reports/
    output_root.mkdir(parents=True, exist_ok=True)
    cam_contract_tex = output_root / "CAM_report.tex"
    cam_contract_payload = output_root / "cam_payload.json"
    cam_contract_log = output_root / "compile.log"
    cam_contract_tex.write_text(
        Path(cam_result["cam_tex"]).read_text(encoding="utf-8", errors="ignore"), encoding="utf-8"
    )
    cam_contract_payload.write_text(
        Path(cam_result["cam_payload"]).read_text(encoding="utf-8", errors="ignore"), encoding="utf-8"
    )
    cam_contract_log.write_text(
        Path(cam_result["compile_log"]).read_text(encoding="utf-8", errors="ignore"), encoding="utf-8"
    )
    cam_contract_pdf = output_root / "CAM_report.pdf"
    if cam_result.get("compile_success") and Path(cam_result["cam_pdf"]).exists():
        cam_contract_pdf.write_bytes(Path(cam_result["cam_pdf"]).read_bytes())
    elif cam_contract_pdf.exists():
        cam_contract_pdf.unlink()

    final = {
        "company": company,
        "slug": slug,
        "dataset_presence": ing["dataset_presence"],
        "financial_features": str(proc_dir / "financial_features.json"),
        "financial_history": str(proc_dir / "financial_history.json"),
        "financial_trends": str(proc_dir / "financial_trends.json"),
        "validated_financials": str(proc_dir / "validated_financials.json"),
        "synthetic_gst_features": str(proc_dir / "synthetic_gst_features.json"),
        "synthetic_bank_features": str(proc_dir / "synthetic_bank_features.json"),
        "research_summary": str(research_out),
        "research_evidence": str(research_evidence_out),
        "credit_features": str(proc_dir / "credit_features.json"),
        "decision_trace": str(proc_dir / "decision_trace.json"),
        "scoring_output": str(proc_dir / "scoring_output.json"),
        "cam_payload": cam_result["cam_payload"],
        "cam_tex": cam_result["cam_tex"],
        "cam_pdf": cam_result["cam_pdf"],
        "cam_compile_log": cam_result["compile_log"],
        "cam_compile_success": cam_result["compile_success"],
        "cam_compiler": cam_result["compiler"],
        "cam_compile_error": cam_result["compile_error"],
        "cam_schema_valid": cam_result["schema_valid"],
        "cam_schema_errors": cam_result["schema_errors"],
        "cam_contract_pdf": str(cam_contract_pdf),
        "cam_contract_tex": str(cam_contract_tex),
        "cam_contract_payload": str(cam_contract_payload),
        "cam_contract_log": str(cam_contract_log),
    }

    # Databricks-compatible Bronze/Silver/Gold persistence (Spark if available, else local fallback).
    spark = None
    try:
        from pyspark.sql import SparkSession  # type: ignore

        spark = SparkSession.getActiveSession()
    except Exception:
        spark = None
    table_writes = write_databricks_tables(
        payloads={
            "bronze.company_raw_files": {"company": company, "dataset_presence": ing["dataset_presence"]},
            "bronze.research_raw": {"company": company, "research_summary_path": str(research_out)},
            "silver.financial_extraction": {"company": company, "financial_history_path": str(proc_dir / "financial_history.json")},
            "silver.research_evidence": {"company": company, "research_evidence_path": str(research_evidence_out)},
            "silver.officer_inputs": {"company": company, "officer_inputs": officer_inputs},
            "gold.credit_features": {"company": company, "credit_features_path": str(proc_dir / "credit_features.json")},
            "gold.credit_scores": {"company": company, "scoring_output_path": str(proc_dir / "scoring_output.json")},
            "gold.cam_payload": {"company": company, "cam_payload_path": cam_result["cam_payload"]},
        },
        spark=spark,
        local_base_dir=root / "data" / "databricks",
    )
    final["databricks_table_writes"] = table_writes
    audit_path = _write_financial_audit(
        root,
        company,
        ing.get("financial_history", {}),
        financial_trends,
        ing.get("anomalies", []),
    )
    final["financial_audit_report"] = audit_path
    final["score_audit_report"] = str(score_audit_path)
    if debug_financials:
        debug_financial_path = debug_dir / f"financial_debug_{slug}.json"
        debug_payload = {
            "company": company,
            "raw_mapped_rows": [
                {
                    "year": row.get("year"),
                    "source": row.get("source"),
                    "source_rows": row.get("source_rows", {}),
                    "mapping_confidence": row.get("mapping_confidence", {}),
                    "unit_confidence": row.get("unit_confidence"),
                    "unit_uncertain": row.get("unit_uncertain"),
                }
                for row in ing.get("financial_history", {}).get("yearly_data", [])
            ],
            "normalized_financial_history": ing.get("financial_history", {}),
            "financial_trends": financial_trends,
            "validated_financials": validated_financials,
            "anomalies": ing.get("anomalies", []),
        }
        debug_financial_path.write_text(json.dumps(debug_payload, indent=2, ensure_ascii=True), encoding="utf-8")
        final["debug_financial_dump"] = str(debug_financial_path)
        final["debug_unit_detection"] = str(root / "outputs" / "debug" / f"unit_detection_{slug}.json")
        final["debug_financial_anomalies"] = str(root / "outputs" / "debug" / f"financial_anomalies_{slug}.json")

    (proc_dir / "pipeline_output.json").write_text(json.dumps(final, indent=2, ensure_ascii=True), encoding="utf-8")

    logger.info("Pipeline completed for %s", company)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Run intelli-credit-engine pipeline")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--debug-financials", action="store_true", help="Emit financial debug artifacts")
    args = parser.parse_args()

    result = run(args.company, debug_financials=args.debug_financials)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
