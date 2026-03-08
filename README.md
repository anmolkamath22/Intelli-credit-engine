# Intelli credit engine

This project helps you run a full credit appraisal workflow from raw company documents to a final credit memo.

You can upload files, run the pipeline, track job status, review the score breakdown, and download the final CAM report.

## what this app does
- reads company datasets from local folders or frontend uploads
- extracts 5-year financial signals
- adds synthetic gst/bank signals when data is missing
- runs litigation/news/director research signals
- computes credit score, decision trace, loan recommendation, and rate
- generates CAM files (`pdf`, `tex`, and payload json)
- supports Databricks-style bronze/silver/gold outputs

## repo layout
```text
intelli-credit-engine/
  src/
    api/
    ingestion/
    research/
    credit_model/
    cam/
    databricks/
  frontend/
  scripts/
  data/
    input/
    processed/
    databricks/
  outputs/
  logs/
  notebooks/databricks/
```

## input folder contract
Put files under:

`data/input/<company_slug>/`

Supported folders:
- `annual_reports/`
- `financial_statements/`
- `balance_sheets/`
- `gst_returns/`
- `bank_statements/`
- `legal_documents/`
- `news_documents/`
- `qualitative/` (optional officer input)

## setup (first time)

### 1) clone and enter project
```bash
git clone <your-repo-url>
cd intelli-credit-engine
```

### 2) create python environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) install system tools
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils texlive-latex-base texlive-latex-recommended texlive-fonts-recommended nodejs npm
```

### 4) install frontend deps
```bash
cd frontend
npm install
cd ..
```

## environment config
Copy sample env files:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Main vars:
- backend:
  - `BACKEND_HOST`
  - `BACKEND_PORT`
  - `API_PREFIX`
  - `ENGINE_STORAGE_ROOT`
  - `CORS_ORIGINS`
- frontend:
  - `VITE_FRONTEND_API_BASE_URL`
  - `VITE_API_BASE` (fallback)

## run locally

### terminal 1: backend
```bash
cd intelli-credit-engine
source .venv/bin/activate
python run_api.py --host 0.0.0.0 --port 8001 --reload
```

### terminal 2: frontend
```bash
cd intelli-credit-engine/frontend
VITE_FRONTEND_API_BASE_URL=http://localhost:8001 npm run dev
```

Open:
- frontend: `http://localhost:5173`
- backend docs: `http://localhost:8001/docs`
- health check: `http://localhost:8001/health`

## run a quick connectivity smoke test
With backend already running:

```bash
cd intelli-credit-engine
source .venv/bin/activate
python scripts/smoke_connectivity.py --base http://localhost:8001 --company "Blue Star Ltd"
```

## api endpoints
- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/debug/config`
- `POST /api/v1/company/upload`
- `POST /api/v1/company/officer-inputs`
- `POST /api/v1/pipeline/run`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/status`
- `GET /api/v1/jobs/{job_id}/result`
- `GET /api/v1/dashboard/{company}`
- `GET /api/v1/download/{company}/{artifact}`

Artifacts:
- `cam_pdf`
- `cam_tex`
- `cam_payload`
- `decision_trace`
- `score_audit`

## docker run
```bash
docker compose up --build
```

Services:
- frontend: `http://localhost:5173`
- backend: `http://localhost:8001`

## databricks notebooks
Run these in order:
1. `notebooks/databricks/00_setup_environment.py`
2. `notebooks/databricks/01_bronze_ingestion.py`
3. `notebooks/databricks/02_silver_extraction.py`
4. `notebooks/databricks/03_research_enrichment.py`
5. `notebooks/databricks/04_gold_scoring.py`
6. `notebooks/databricks/05_cam_generation.py`
7. `notebooks/databricks/06_dashboard_tables.py`

## logs and debug files
- backend logs: `logs/backend.log`
- connectivity audit: `debug/connectivity_audit.json`
- pipeline debug outputs: `outputs/debug/`

## common issues
### frontend opens but results do not load
- check `http://localhost:8001/api/v1/health`
- confirm frontend API base url points to backend
- inspect `logs/backend.log`
- run `scripts/smoke_connectivity.py`

### upload works but job looks stuck
- query `GET /api/v1/jobs/{job_id}/status`
- if failed, inspect `GET /api/v1/jobs/{job_id}/result`

### cam pdf is missing
- confirm job status is `completed`
- check `outputs/cam_reports/<company>/compile.log`
