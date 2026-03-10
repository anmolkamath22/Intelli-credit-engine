# Intelli-Credit Engine

Intelli-Credit Engine is a full-stack credit underwriting platform that turns uploaded company documents into an explainable lending decision and a downloadable CAM report.

## What this project delivers

- Entity onboarding with requested loan amount, tenure, and pricing context
- Multi-source ingestion across annual reports, ALM, shareholding, borrowing profile, portfolio cuts, and optional legal/news documents
- Financial extraction, normalization, trend analysis, and feature engineering
- Secondary intelligence layer (news + litigation + board risk + confidence scoring)
- Decision engine that evaluates the requested facility and recommends approve / approve with conditions / reject
- Professional CAM outputs: `CAM_report.pdf`, `CAM_report.tex`, `cam_payload.json`, `decision_trace.json`

## Tech stack

- Backend: FastAPI + Python
- Frontend: React + Vite
- Report engine: JSON -> deterministic LaTeX renderer -> local PDF compilation
- Retrieval: vector-store based evidence retrieval
- Optional runtime: Docker Compose

## Quick start (local)

### 1) Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in project root:

```env
API_PREFIX=/api/v1
ENGINE_STORAGE_ROOT=./runtime_data
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
MAX_UPLOAD_MB=25
```

Start API:

```bash
python run_api.py --host 0.0.0.0 --port 8001 --reload
```

Health check:

```bash
curl http://127.0.0.1:8001/api/v1/health
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:5173`

## Recommended demo flow

1. Save onboarding details (entity + loan ask + requested rate)
2. Upload files category-wise (one category at a time)
3. Run classification and schema mapping review
4. Generate extraction preview
5. Save officer inputs
6. Run full credit evaluation
7. Download CAM and trace artifacts

## Output artifacts

- `data/processed/<company_slug>/financial_history.json`
- `data/processed/<company_slug>/financial_trends.json`
- `data/processed/<company_slug>/credit_features.json`
- `data/processed/<company_slug>/decision_trace.json`
- `outputs/cam_reports/<company_slug>/CAM_report.pdf`
- `outputs/cam_reports/<company_slug>/CAM_report.tex`
- `outputs/cam_reports/<company_slug>/cam_payload.json`

## Repository layout

- `src/` core engine modules (ingestion, research, scoring, CAM, API)
- `frontend/` React UI
- `scripts/` pipeline runners
- `data/input/` uploaded source documents
- `data/processed/` generated structured outputs
- `outputs/` reports and debug artifacts

## Docker run (optional)

```bash
docker compose up --build
```

Frontend: `http://localhost:5173`  
Backend health: `http://localhost:8001/api/v1/health`

## Troubleshooting

- Frontend says backend offline:
  - verify backend is running on port `8001`
  - verify `API_PREFIX` and CORS values in `.env`
- Upload path/runtime issues:
  - set `ENGINE_STORAGE_ROOT=./runtime_data`
  - restart backend after `.env` changes
- Port already in use:
  - run backend on a different port (e.g. `8002`) and update frontend API base accordingly

## Security notes

- Never commit secrets, tokens, or personal `.env` values
- Keep only placeholder config in `.env.example`
- Use sanitized upload handling and category-wise validation in production
