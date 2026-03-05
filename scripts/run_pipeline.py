"""Unified intelli-credit-engine pipeline runner (upgraded for partial datasets)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from scripts.run_cam_generation import run_cam
from src.analysis.financial_narrative_generator import generate_financial_narrative
from src.credit_model.circular_trading_detector import detect_circular_trading
from src.credit_model.decision_trace import build_decision_trace
from src.credit_model.feature_engineering import build_credit_features
from src.credit_model.financial_trend_analysis import compute_financial_trends
from src.credit_model.scoring_model import score_credit
from src.ingestion.data_ingestor import DataIngestor
from src.officer_portal.credit_officer_inputs import load_officer_inputs
from src.research.research_agent import run_research_agent
from src.utils.logger import get_logger
from src.utils.text_processing import slugify, split_words
from src.vector_store.embedding_builder import EmbeddingBuilder
from src.vector_store.retriever import VectorRetriever


def _load_cfg(root: Path) -> dict:
    return yaml.safe_load((root / "configs" / "pipeline_config.yaml").read_text(encoding="utf-8"))


def run(company: str) -> dict:
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
        for chunk in split_words(d.get("text", ""), chunk_size=chunk_size, overlap=overlap):
            retriever.add(source=d.get("source", "unknown"), chunk=chunk)

    proc_dir = processed_root / slug
    for f in [
        proc_dir / "financial_features.json",
        proc_dir / "financial_history.json",
        proc_dir / "synthetic_gst_features.json",
        proc_dir / "synthetic_bank_features.json",
    ]:
        if f.exists():
            text = f.read_text(encoding="utf-8", errors="ignore")
            for chunk in split_words(text, chunk_size=chunk_size, overlap=overlap):
                retriever.add(source=str(f), chunk=chunk)

    research_out = proc_dir / "research_summary.json"
    research = run_research_agent(
        company_name=company,
        financials=ing["financials"],
        company_dir=ing["company_dir"],
        retriever=retriever,
        output_path=research_out,
        top_k=int(cfg.get("retrieval", {}).get("top_k", 5)),
    )

    officer_inputs = load_officer_inputs(ing["company_dir"] / "qualitative" / "officer_inputs.json")

    gst_sales = float(ing["gst_signals"].get("gst_sales_estimate") or ing["financials"].get("revenue") or 0.0)
    circular_flags = detect_circular_trading(gst_sales=gst_sales, bank_df=ing["bank_df"])
    financial_trends = compute_financial_trends(ing.get("financial_history", {}))
    trend_narrative = generate_financial_narrative(company, financial_trends, ing.get("financial_history", {}))
    (proc_dir / "financial_trends.json").write_text(
        json.dumps(financial_trends, indent=2, ensure_ascii=True), encoding="utf-8"
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

    (proc_dir / "credit_features.json").write_text(json.dumps(features, indent=2, ensure_ascii=True), encoding="utf-8")
    (proc_dir / "decision_trace.json").write_text(json.dumps(trace, indent=2, ensure_ascii=True), encoding="utf-8")
    (proc_dir / "scoring_output.json").write_text(json.dumps(scoring, indent=2, ensure_ascii=True), encoding="utf-8")

    # Expand vector store with research + scoring artifacts before CAM generation.
    for f in [
        proc_dir / "research_summary.json",
        proc_dir / "financial_trends.json",
        proc_dir / "credit_features.json",
        proc_dir / "decision_trace.json",
        proc_dir / "scoring_output.json",
    ]:
        if f.exists():
            text = f.read_text(encoding="utf-8", errors="ignore")
            for chunk in split_words(text, chunk_size=chunk_size, overlap=overlap):
                retriever.add(source=str(f), chunk=chunk)

    cam_result = run_cam(
        company=company,
        payload={
            "slug": slug,
            "financials": ing["financials"],
            "financial_history": ing.get("financial_history", {}),
            "financial_trends": financial_trends,
            "trend_narrative": trend_narrative,
            "dataset_presence": ing.get("dataset_presence", {}),
            "research": research,
            "features": features,
            "scoring": scoring,
            "trace": trace,
        },
        output_dir=output_root,
    )

    # Contract output alias
    cam_contract_pdf = output_root / slug / "CAM_report.pdf"
    cam_contract_pdf.parent.mkdir(parents=True, exist_ok=True)
    cam_contract_pdf.write_bytes(Path(cam_result["pdf"]).read_bytes())
    # Legacy flat alias for compatibility with earlier output naming.
    legacy_cam_pdf = output_root / f"{slug}_cam.pdf"
    legacy_cam_pdf.write_bytes(cam_contract_pdf.read_bytes())
    legacy_cam_txt = None
    docx_or_txt = Path(cam_result["docx"])
    if docx_or_txt.suffix.lower() == ".txt" and docx_or_txt.exists():
        legacy_cam_txt = output_root / f"{slug}_cam.txt"
        legacy_cam_txt.write_text(docx_or_txt.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")

    final = {
        "company": company,
        "slug": slug,
        "dataset_presence": ing["dataset_presence"],
        "financial_features": str(proc_dir / "financial_features.json"),
        "financial_history": str(proc_dir / "financial_history.json"),
        "financial_trends": str(proc_dir / "financial_trends.json"),
        "synthetic_gst_features": str(proc_dir / "synthetic_gst_features.json"),
        "synthetic_bank_features": str(proc_dir / "synthetic_bank_features.json"),
        "research_summary": str(research_out),
        "credit_features": str(proc_dir / "credit_features.json"),
        "decision_trace": str(proc_dir / "decision_trace.json"),
        "scoring_output": str(proc_dir / "scoring_output.json"),
        "cam_docx": cam_result["docx"],
        "cam_pdf": cam_result["pdf"],
        "cam_contract_pdf": str(cam_contract_pdf),
        "legacy_cam_pdf": str(legacy_cam_pdf),
        "legacy_cam_txt": str(legacy_cam_txt) if legacy_cam_txt else None,
    }
    (proc_dir / "pipeline_output.json").write_text(json.dumps(final, indent=2, ensure_ascii=True), encoding="utf-8")

    logger.info("Pipeline completed for %s", company)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Run intelli-credit-engine pipeline")
    parser.add_argument("--company", required=True, help="Company name")
    args = parser.parse_args()

    result = run(args.company)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
