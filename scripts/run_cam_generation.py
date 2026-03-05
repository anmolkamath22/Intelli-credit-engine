"""CAM generation runner from processed artifacts."""

from __future__ import annotations

from pathlib import Path

from src.cam.cam_formatter import save_cam_docx, save_cam_pdf
from src.cam.cam_generator import build_cam_sections


def run_cam(company: str, payload: dict, output_dir: Path) -> dict:
    """Generate CAM outputs (DOCX + PDF) for one company."""
    sections = build_cam_sections(
        company=company,
        financials=payload["financials"],
        research=payload["research"],
        features=payload["features"],
        scoring=payload["scoring"],
        trace=payload["trace"],
        financial_history=payload.get("financial_history"),
        financial_trends=payload.get("financial_trends"),
        trend_narrative=payload.get("trend_narrative"),
        dataset_presence=payload.get("dataset_presence"),
    )

    slug = payload.get("slug", company.lower().replace(" ", "_"))
    company_out = output_dir / slug
    company_out.mkdir(parents=True, exist_ok=True)

    docx_path = company_out / "CAM_report.docx"
    pdf_path = company_out / "CAM_report.pdf"

    final_docx_path = save_cam_docx(sections, docx_path)
    final_pdf_path = save_cam_pdf(sections, pdf_path)

    return {"docx": str(final_docx_path), "pdf": str(final_pdf_path), "sections": sections}
