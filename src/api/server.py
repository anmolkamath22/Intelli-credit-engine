"""FastAPI backend for the credit engine app."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from scripts.run_pipeline import run as run_pipeline
from src.utils.text_processing import slugify

ROOT = Path(__file__).resolve().parents[2]
STORAGE_ROOT = Path(os.getenv("ENGINE_STORAGE_ROOT", str(ROOT / "data")))
INPUT_ROOT = STORAGE_ROOT / "input"
PROCESSED_ROOT = STORAGE_ROOT / "processed"
CAM_ROOT = ROOT / "outputs" / "cam_reports"
LOGS_ROOT = ROOT / "logs"
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")

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


class ApiError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400, details: Any | None = None) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details


def _setup_logger() -> logging.Logger:
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("intelli_credit_api")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOGS_ROOT / "backend.log", encoding="utf-8")
    sh = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


logger = _setup_logger()

app = FastAPI(title="Intelli Credit Engine API", version="1.1.0")


# keep defaults strict in local dev and expand through CORS_ORIGINS when needed
def _allowed_origins() -> list[str]:
    cfg = os.getenv("CORS_ORIGINS", "")
    if cfg.strip():
        return [x.strip() for x in cfg.split(",") if x.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_job_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _ok(message: str = "ok", data: Any | None = None, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"success": True, "message": message}
    if data is not None:
        out["data"] = data
    out.update(extra)
    return out


def _company_dirs(company: str) -> tuple[str, Path, Path, Path]:
    slug = slugify(company)
    in_dir = INPUT_ROOT / slug
    proc = PROCESSED_ROOT / slug
    cam = CAM_ROOT / slug
    in_dir.mkdir(parents=True, exist_ok=True)
    proc.mkdir(parents=True, exist_ok=True)
    cam.mkdir(parents=True, exist_ok=True)
    return slug, in_dir, proc, cam


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _set_job(job_id: str, payload: dict[str, Any]) -> None:
    with _job_lock:
        existing = _jobs.get(job_id, {})
        existing.update(payload)
        _jobs[job_id] = existing


def _read_gold_tables(company: str) -> dict[str, Any]:
    base = ROOT / "data" / "databricks" / "gold"
    out = {}
    for key in ["credit_features", "credit_scores", "cam_payload"]:
        payload = _read_json(base / key / "latest.json")
        if payload.get("company") == company:
            out[key] = payload
    return out


def _job_status_payload(job_id: str, job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "status": job.get("status", "queued"),
        "progress": job.get("progress", 0),
        "message": job.get("message", ""),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
    }


def _run_job(job_id: str, company: str, debug_financials: bool) -> None:
    started = datetime.now(timezone.utc).isoformat()
    _set_job(
        job_id,
        {
            "status": "processing",
            "progress": 20,
            "message": "Pipeline started",
            "started_at": started,
        },
    )
    logger.info("route=pipeline_run stage=started job_id=%s company=%s", job_id, company)
    try:
        result = run_pipeline(company, debug_financials=debug_financials)
        _set_job(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "message": "Pipeline completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": result,
                "error": None,
            },
        )
        logger.info("route=pipeline_run stage=completed job_id=%s company=%s", job_id, company)
    except Exception as exc:
        _set_job(
            job_id,
            {
                "status": "failed",
                "progress": 100,
                "message": "Pipeline failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": None,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        logger.exception("route=pipeline_run stage=failed job_id=%s company=%s error=%s", job_id, company, exc)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["x-request-id"] = request_id
        logger.info(
            "route=%s method=%s status=%s request_id=%s duration_ms=%s",
            request.url.path,
            request.method,
            response.status_code,
            request_id,
            duration_ms,
        )
        return response
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception(
            "route=%s method=%s status=500 request_id=%s duration_ms=%s error=%s",
            request.url.path,
            request.method,
            request_id,
            duration_ms,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "internal_error",
                "message": "Internal server error",
                "details": str(exc),
                "request_id": request_id,
            },
        )


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": "http_error",
            "message": str(exc.detail),
            "details": None,
        },
    )


def _health_payload() -> dict[str, Any]:
    storage_checks = {
        "input_root": str(INPUT_ROOT),
        "processed_root": str(PROCESSED_ROOT),
        "cam_root": str(CAM_ROOT),
        "logs_root": str(LOGS_ROOT),
    }
    for p in [INPUT_ROOT, PROCESSED_ROOT, CAM_ROOT, LOGS_ROOT]:
        p.mkdir(parents=True, exist_ok=True)
    deps = {
        "fastapi": True,
        "python_docx": True,
    }
    return {
        "status": "ok",
        "storage": storage_checks,
        "cors_origins": _allowed_origins(),
        "api_prefix": API_PREFIX,
        "dependencies": deps,
    }


@app.get("/health")
def health_root() -> dict[str, Any]:
    return _ok(data=_health_payload())


@app.get(f"{API_PREFIX}/health")
def health_api() -> dict[str, Any]:
    return _ok(data=_health_payload())


@app.get("/debug/config")
@app.get(f"{API_PREFIX}/debug/config")
def debug_config() -> dict[str, Any]:
    return _ok(
        data={
            "root": str(ROOT),
            "storage_root": str(STORAGE_ROOT),
            "input_root": str(INPUT_ROOT),
            "processed_root": str(PROCESSED_ROOT),
            "cam_root": str(CAM_ROOT),
            "api_prefix": API_PREFIX,
            "cors_origins": _allowed_origins(),
        }
    )


@app.get(f"{API_PREFIX}/companies")
def list_companies() -> dict[str, Any]:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    companies = sorted([p.name for p in INPUT_ROOT.iterdir() if p.is_dir()])
    return _ok(data={"companies": companies})


@app.post(f"{API_PREFIX}/company/upload")
async def upload_files(
    company: str = Form(...),
    data_type: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    if data_type not in DATASET_FOLDERS:
        raise ApiError("invalid_data_type", f"Unsupported data_type: {data_type}", status_code=400)

    upload_job_id = str(uuid.uuid4())
    slug, company_input_dir, _, _ = _company_dirs(company)
    target_dir = company_input_dir / DATASET_FOLDERS[data_type]
    target_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for upload in files:
        name = Path(upload.filename or "uploaded.bin").name
        dest = target_dir / name
        content = await upload.read()
        dest.write_bytes(content)
        saved.append(str(dest.relative_to(ROOT)))

    logger.info(
        "route=upload stage=completed job_id=%s company=%s data_type=%s files=%s",
        upload_job_id,
        company,
        data_type,
        len(saved),
    )
    return {
        "success": True,
        "job_id": upload_job_id,
        "message": "Files uploaded successfully",
        "saved_files": saved,
        "company": company,
        "company_slug": slug,
        "data_type": data_type,
    }


@app.post(f"{API_PREFIX}/company/officer-inputs")
def save_officer_inputs(payload: OfficerInputPayload) -> dict[str, Any]:
    slug, company_input_dir, _, _ = _company_dirs(payload.company)
    qual_dir = company_input_dir / "qualitative"
    qual_dir.mkdir(parents=True, exist_ok=True)
    out = qual_dir / "officer_inputs.json"
    out.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    return _ok(message="Officer inputs saved", data={"company": payload.company, "slug": slug, "saved_to": str(out.relative_to(ROOT))})


@app.post(f"{API_PREFIX}/pipeline/run")
def run_pipeline_endpoint(payload: RunRequest, bg: BackgroundTasks) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    _set_job(
        job_id,
        {
            "status": "queued",
            "progress": 5,
            "message": "Job queued",
            "company": payload.company,
            "debug_financials": payload.debug_financials,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
            "error": None,
        },
    )
    bg.add_task(_run_job, job_id, payload.company, payload.debug_financials)
    return {
        "success": True,
        "job_id": job_id,
        "message": "Pipeline job queued",
        "status": "queued",
    }


@app.get(f"{API_PREFIX}/jobs/{{job_id}}")
def get_job(job_id: str) -> dict[str, Any]:
    with _job_lock:
        data = _jobs.get(job_id)
    if not data:
        raise ApiError("job_not_found", "Job not found", status_code=404)
    return _ok(data=_job_status_payload(job_id, data))


@app.get("/jobs/{job_id}/status")
@app.get(f"{API_PREFIX}/jobs/{{job_id}}/status")
def get_job_status(job_id: str) -> dict[str, Any]:
    with _job_lock:
        data = _jobs.get(job_id)
    if not data:
        raise ApiError("job_not_found", "Job not found", status_code=404)
    return {
        "success": True,
        **_job_status_payload(job_id, data),
    }


@app.get("/jobs/{job_id}/result")
@app.get(f"{API_PREFIX}/jobs/{{job_id}}/result")
def get_job_result(job_id: str) -> dict[str, Any]:
    with _job_lock:
        data = _jobs.get(job_id)
    if not data:
        raise ApiError("job_not_found", "Job not found", status_code=404)
    status = data.get("status")
    if status in {"queued", "processing"}:
        return {
            "success": False,
            "job_id": job_id,
            "status": status,
            "message": "Job still in progress",
            "result": None,
        }
    if status == "failed":
        return {
            "success": False,
            "job_id": job_id,
            "status": "failed",
            "message": "Job failed",
            "error_code": "job_failed",
            "details": data.get("error"),
            "result": None,
        }
    return {
        "success": True,
        "job_id": job_id,
        "status": "completed",
        "message": "Job completed",
        "result": data.get("result", {}),
    }


@app.get(f"{API_PREFIX}/financials/{{company}}")
def get_financials(company: str) -> dict[str, Any]:
    _, _, proc_dir, _ = _company_dirs(company)
    return _ok(
        data={
            "financial_history": _read_json(proc_dir / "financial_history.json"),
            "financial_trends": _read_json(proc_dir / "financial_trends.json"),
            "validated_financials": _read_json(proc_dir / "validated_financials.json"),
        }
    )


@app.get(f"{API_PREFIX}/research/{{company}}")
def get_research(company: str) -> dict[str, Any]:
    _, _, proc_dir, _ = _company_dirs(company)
    return _ok(
        data={
            "research_summary": _read_json(proc_dir / "research_summary.json"),
            "research_evidence": _read_json(proc_dir / "research_evidence.json"),
        }
    )


@app.get(f"{API_PREFIX}/scores/{{company}}")
def get_scores(company: str) -> dict[str, Any]:
    slug, _, proc_dir, _ = _company_dirs(company)
    score = _read_json(proc_dir / "scoring_output.json")
    trace = _read_json(proc_dir / "decision_trace.json")
    score_audit = _read_json(ROOT / "outputs" / "debug" / f"score_audit_{slug}.json")
    return _ok(data={"scoring_output": score, "decision_trace": trace, "score_audit": score_audit})


@app.get(f"{API_PREFIX}/dashboard/{{company}}")
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
        "cam_dir": str(cam_dir.relative_to(ROOT)),
    }
    return _ok(data=out)


@app.get(f"{API_PREFIX}/download/{{company}}/{{artifact}}")
def download_artifact(company: str, artifact: str) -> FileResponse:
    slug, _, proc_dir, cam_dir = _company_dirs(company)
    if artifact not in ARTIFACTS:
        raise ApiError("invalid_artifact", f"Unsupported artifact: {artifact}", status_code=400)

    if artifact == "decision_trace":
        path = proc_dir / ARTIFACTS[artifact]
    elif artifact == "score_audit":
        path = ROOT / "outputs" / "debug" / f"score_audit_{slug}.json"
    else:
        path = cam_dir / ARTIFACTS[artifact]
        if not path.exists():
            path = ROOT / "outputs" / "cam_reports" / ARTIFACTS[artifact]

    if not path.exists():
        raise ApiError("artifact_not_found", f"Artifact not found: {path}", status_code=404)
    return FileResponse(path=str(path), filename=path.name)
