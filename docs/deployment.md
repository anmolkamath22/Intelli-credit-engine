# Deployment Guide

## Local Demo Deployment

### 1. Backend
```bash
cd intelli-credit-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_api.py
```

### 2. Frontend
```bash
cd intelli-credit-engine/frontend
npm install
npm run build
npm run preview
```

### 3. Production-like split deployment
- Backend: deploy FastAPI app to Render/Fly.io/Railway/EC2.
- Frontend: deploy Vite build to Vercel/Netlify.
- Configure frontend env:
  - `VITE_API_BASE=https://<backend-host>`

## Databricks Deployment

1. Import notebooks from `notebooks/databricks/` into Databricks workspace.
2. Attach a cluster with Delta support.
3. Run notebooks sequentially from `00_setup_environment` to `06_dashboard_tables`.
4. Create a Databricks Job with this sequence for scheduled runs.

## API Surface
- `POST /api/v1/company/upload`
- `POST /api/v1/company/officer-inputs`
- `POST /api/v1/pipeline/run`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/dashboard/{company}`
- `GET /api/v1/download/{company}/{artifact}`

## Download Artifacts
Supported `{artifact}` values:
- `cam_pdf`
- `cam_tex`
- `cam_payload`
- `decision_trace`
- `score_audit`
