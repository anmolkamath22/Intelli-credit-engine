"""FastAPI backend for intelli-credit-engine frontend and integrations."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from scripts.run_pipeline import run as run_pipeline
from src.utils.text_processing import slugify

ROOT = Path(__file__).resolve().parents[2]
INPUT_ROOT = ROOT / "data" / "input"
PROCESSED_ROOT = ROOT / "data" / "processed"
CAM_ROOT = ROOT / "outputs" / "cam_reports"

DATASET_FOLDERS = {
    "annual_reports": "annual_reports",
    "financial_statements": "financial_statements",
    "balance_sheets": "balance_sheets",
    "gst_returns": "gst_returns",
    "bank_statements": "bank_statements",
    "legal_documents": "legal_documents",
    "news_documents": "news_documents",
}

ARTIFACTS = {
    "cam_pdf": "CAM_report.pdf",
    "cam_tex": "CAM_report.tex",
    "cam_payload": "cam_payload.json",
    "decision_trace": "decision_trace.json",
    "score_audit": "score_audit.json",
}


class OfficerInputPayload(BaseModel):
    company: str
    factory_utilization: float = Field(ge=0.0, le=1.0)
    management_credibility: float = Field(ge=0.0, le=1.0)
    inventory_build_up: float = Field(ge=0.0, le=1.0)
    supply_chain_risk: float = Field(ge=0.0, le=1.0)
    collateral_notes: str = ""
    channel_checks: str = ""


class RunRequest(BaseModel):
    company: str
    debug_financials: bool = False


app = FastAPI(title="Intelli Credit Engine API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_job_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _company_dirs(company: str) -> tuple[str, Path, Path, Path]:
    slug = slugify(company)
    return slug, INPUT_ROOT / slug, PROCESSED_ROOT / slug, CAM_ROOT / slug


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_gold_tables(company: str) -> dict[str, Any]:
    """Read local Databricks-fallback Gold tables for dashboard APIs."""
    base = ROOT / "data" / "databricks" / "gold"
    out = {}
    for key in ["credit_features", "credit_scores", "cam_payload"]:
        payload = _read_json(base / key / "latest.json")
        if payload.get("company") == company:
            out[key] = payload
    return out


def _set_job(job_id: str, payload: dict[str, Any]) -> None:
    with _job_lock:
        existing = _jobs.get(job_id, {})
        existing.update(payload)
        _jobs[job_id] = existing


def _run_job(job_id: str, company: str, debug_financials: bool) -> None:
    _set_job(job_id, {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()})
    try:
        result = run_pipeline(company, debug_financials=debug_financials)
        _set_job(
            job_id,
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": result,
                "error": None,
            },
        )
    except Exception as exc:
        _set_job(
            job_id,
            {
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": None,
                "error": str(exc),
            },
        )


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/companies")
def list_companies() -> dict[str, Any]:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    companies = sorted([p.name for p in INPUT_ROOT.iterdir() if p.is_dir()])
    return {"companies": companies}


@app.post("/api/v1/company/upload")
async def upload_files(
    company: str = Form(...),
    data_type: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    if data_type not in DATASET_FOLDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported data_type: {data_type}")

    slug, company_input_dir, _, _ = _company_dirs(company)
    target_dir = company_input_dir / DATASET_FOLDERS[data_type]
    target_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for upload in files:
        name = Path(upload.filename or "uploaded.bin").name
        dest = target_dir / name
        content = await upload.read()
        dest.write_bytes(content)
        saved.append(str(dest))

    return {
        "company": company,
        "slug": slug,
        "data_type": data_type,
        "files_saved": saved,
    }


@app.post("/api/v1/company/officer-inputs")
def save_officer_inputs(payload: OfficerInputPayload) -> dict[str, Any]:
    slug, company_input_dir, _, _ = _company_dirs(payload.company)
    qual_dir = company_input_dir / "qualitative"
    qual_dir.mkdir(parents=True, exist_ok=True)
    out = qual_dir / "officer_inputs.json"
    out.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    return {"company": payload.company, "slug": slug, "saved_to": str(out)}


@app.post("/api/v1/pipeline/run")
def run_pipeline_endpoint(payload: RunRequest, bg: BackgroundTasks) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    _set_job(
        job_id,
        {
            "status": "queued",
            "company": payload.company,
            "debug_financials": payload.debug_financials,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error": None,
        },
    )
    bg.add_task(_run_job, job_id, payload.company, payload.debug_financials)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with _job_lock:
        data = _jobs.get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return data


@app.get("/api/v1/financials/{company}")
def get_financials(company: str) -> dict[str, Any]:
    _, _, proc_dir, _ = _company_dirs(company)
    return {
        "financial_history": _read_json(proc_dir / "financial_history.json"),
        "financial_trends": _read_json(proc_dir / "financial_trends.json"),
        "validated_financials": _read_json(proc_dir / "validated_financials.json"),
    }


@app.get("/api/v1/research/{company}")
def get_research(company: str) -> dict[str, Any]:
    _, _, proc_dir, _ = _company_dirs(company)
    return {
        "research_summary": _read_json(proc_dir / "research_summary.json"),
        "research_evidence": _read_json(proc_dir / "research_evidence.json"),
    }


@app.get("/api/v1/scores/{company}")
def get_scores(company: str) -> dict[str, Any]:
    slug, _, proc_dir, _ = _company_dirs(company)
    score = _read_json(proc_dir / "scoring_output.json")
    trace = _read_json(proc_dir / "decision_trace.json")
    score_audit = _read_json(ROOT / "outputs" / "debug" / f"score_audit_{slug}.json")
    return {"scoring_output": score, "decision_trace": trace, "score_audit": score_audit}


@app.get("/api/v1/dashboard/{company}")
def get_dashboard(company: str) -> dict[str, Any]:
    slug, _, proc_dir, cam_dir = _company_dirs(company)
    out = {
        "company": company,
        "slug": slug,
        "gold_tables": _read_gold_tables(company),
        "pipeline_output": _read_json(proc_dir / "pipeline_output.json"),
        "credit_features": _read_json(proc_dir / "credit_features.json"),
        "scoring_output": _read_json(proc_dir / "scoring_output.json"),
        "decision_trace": _read_json(proc_dir / "decision_trace.json"),
        "research_summary": _read_json(proc_dir / "research_summary.json"),
        "research_evidence": _read_json(proc_dir / "research_evidence.json"),
        "financial_history": _read_json(proc_dir / "financial_history.json"),
        "financial_trends": _read_json(proc_dir / "financial_trends.json"),
        "cam_available": (cam_dir / "CAM_report.pdf").exists(),
        "cam_dir": str(cam_dir),
    }
    return out


@app.get("/api/v1/download/{company}/{artifact}")
def download_artifact(company: str, artifact: str) -> FileResponse:
    slug, _, proc_dir, cam_dir = _company_dirs(company)
    if artifact not in ARTIFACTS:
        raise HTTPException(status_code=400, detail=f"Unsupported artifact: {artifact}")

    if artifact == "decision_trace":
        path = proc_dir / ARTIFACTS[artifact]
    elif artifact == "score_audit":
        path = ROOT / "outputs" / "debug" / f"score_audit_{slug}.json"
    else:
        path = cam_dir / ARTIFACTS[artifact]
        # Fallback to run-level contract artifact for latest pipeline execution.
        if not path.exists():
            path = ROOT / "outputs" / "cam_reports" / ARTIFACTS[artifact]

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")
    return FileResponse(path=str(path), filename=path.name)
