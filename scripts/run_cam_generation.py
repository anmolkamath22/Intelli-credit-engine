"""CAM generation runner from processed artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from src.cam.cam_generator import build_cam_payload
from src.cam.cam_json_schema import validate_cam_payload
from src.cam.latex_compiler import compile_latex
from src.cam.latex_renderer import render_cam_payload_to_latex


def run_cam(company: str, payload: dict, output_dir: Path) -> dict:
    """Generate CAM outputs via JSON -> LaTeX -> local compilation."""
    cam_payload = build_cam_payload(
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
        validated_financials=payload.get("validated_financials"),
        cam_evidence=payload.get("cam_evidence"),
    )
    valid, errors = validate_cam_payload(cam_payload)

    slug = payload.get("slug", company.lower().replace(" ", "_"))
    company_out = output_dir / slug
    company_out.mkdir(parents=True, exist_ok=True)

    payload_path = company_out / "cam_payload.json"
    tex_path = company_out / "CAM_report.tex"
    log_path = company_out / "compile.log"
    pdf_path = company_out / "CAM_report.pdf"
    # Remove stale non-LaTeX artifacts from older pipeline versions.
    for legacy in [company_out / "CAM_report.txt", company_out / "CAM_report.docx"]:
        if legacy.exists():
            legacy.unlink()

    payload_path.write_text(json.dumps(cam_payload, indent=2, ensure_ascii=True), encoding="utf-8")
    latex_doc = render_cam_payload_to_latex(cam_payload)
    tex_path.write_text(latex_doc, encoding="utf-8")
    compile_result = compile_latex(tex_path, log_path)
    if not compile_result.get("success") and pdf_path.exists():
        pdf_path.unlink()

    return {
        "cam_payload": str(payload_path),
        "cam_tex": str(tex_path),
        "cam_pdf": str(pdf_path),
        "compile_log": str(log_path),
        "compile_success": bool(compile_result.get("success")),
        "compiler": compile_result.get("compiler"),
        "compile_error": compile_result.get("error"),
        "schema_valid": valid,
        "schema_errors": errors,
    }
