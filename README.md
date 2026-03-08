---
title: intelli-credit-engine
emoji: 💳
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---


# Intelli credit engine

A full-stack credit appraisal app for hackathon demos.

It ingests company documents, runs financial + risk analysis, produces a credit decision, and generates downloadable CAM outputs (`pdf`, `tex`, `json`).

## deployment model
Primary deployment target is a **single Docker container** (best for free hosting and avoids frontend-backend mismatch).

Supported paths:
1. **primary**: Hugging Face Spaces (Docker)
2. **fallback**: Vercel frontend + Render backend
3. **optional fallback**: Streamlit app (`streamlit_app.py`)

Deployment audit report:
- `deploy/deployment_audit.json`

## what is included
- frontend upload + status + results UI
- backend API with job lifecycle endpoints
- structured logging (`logs/backend.log`)
- health and debug endpoints
- CAM generation and downloads
- Databricks-compatible bronze/silver/gold output writes

## project layout
```text
intelli-credit-engine/
  src/
    api/
    ingestion/
    research/
    credit_model/
    cam/
  frontend/
  scripts/
  data/
  outputs/
  logs/
  deploy/
  Dockerfile
  docker-compose.yml
```

## required input layout
Place files under:

`data/input/<company_slug>/`

supported folders:
- `annual_reports/`
- `financial_statements/`
- `balance_sheets/`
- `gst_returns/`
- `bank_statements/`
- `legal_documents/`
- `news_documents/`
- `qualitative/` (optional officer input)

## local run (without docker)

### 1) setup
```bash
git clone <your-repo-url>
cd intelli-credit-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) system packages (linux)
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils texlive-latex-base texlive-latex-recommended texlive-fonts-recommended nodejs npm
```

### 3) frontend install
```bash
cd frontend
npm install
cd ..
```

### 4) env files
```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

### 5) run backend
```bash
source .venv/bin/activate
python run_api.py --host 0.0.0.0 --port 8001 --reload
```

### 6) run frontend (new terminal)
```bash
cd frontend
VITE_FRONTEND_API_BASE_URL=http://localhost:8001 npm run dev
```

open:
- frontend: `http://localhost:5173`
- backend docs: `http://localhost:8001/docs`
- backend health: `http://localhost:8001/health`

## local run across two PCs (same Wi-Fi/LAN)

Use this when backend/frontend are on one machine and teammate opens from another machine.

1. On host machine, find LAN IP (example: `192.168.29.93`).
2. Start backend on host machine:
```bash
python run_api.py --host 0.0.0.0 --port 8001 --reload
```
3. Start frontend on host machine:
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```
4. On teammate machine, open:
- `http://<HOST_IP>:5173`
- `http://<HOST_IP>:8001/health`

Important:
- `0.0.0.0` is a bind address, not a browser URL.
- opening `http://0.0.0.0:8001` in browser will fail (`ERR_ADDRESS_INVALID`).

## single-container docker run (recommended)

```bash
docker compose up --build
```

open:
- app: `http://localhost:7860`
- health: `http://localhost:7860/health`
- api docs: `http://localhost:7860/docs`

## API endpoints
- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/debug/config`
- `POST /api/v1/company/upload`
- `POST /api/v1/company/officer-inputs`
- `POST /api/v1/pipeline/run`
- `GET /api/v1/jobs/{job_id}/status`
- `GET /api/v1/jobs/{job_id}/result`
- `GET /api/v1/dashboard/{company}`
- `GET /api/v1/download/{company}/{artifact}`

artifact options:
- `cam_pdf`
- `cam_tex`
- `cam_payload`
- `decision_trace`
- `score_audit`

## smoke test
With backend running:

```bash
source .venv/bin/activate
python scripts/smoke_connectivity.py --base http://localhost:8001 --company "Blue Star Ltd"
```

## hugging face spaces (primary)
See:
- `deploy/huggingface_spaces.md`

Use Docker Space and point to this repo.

## vercel + render fallback
See:
- `deploy/vercel_render_fallback.md`

## streamlit fallback
See:
- `deploy/streamlit_fallback.md`

Run locally:
```bash
streamlit run streamlit_app.py
```

## environment variables
Backend (`.env`):
- `BACKEND_HOST`
- `BACKEND_PORT`
- `PORT`
- `API_PREFIX`
- `ENGINE_STORAGE_ROOT`
- `CORS_ORIGINS`

Frontend (`frontend/.env`):
- `VITE_FRONTEND_API_BASE_URL`
- `VITE_API_BASE`

## storage behavior in hosted mode
Free tiers usually provide ephemeral disk.
- uploads and generated files are available while app is running
- files may disappear after restart/redeploy

## troubleshooting
- check backend logs: `logs/backend.log`
- check connectivity audit: `deploy/deployment_audit.json`
- check job status endpoint before fetching results
- if UI waits forever, verify API base URL in frontend env
