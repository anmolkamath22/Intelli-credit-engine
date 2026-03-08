---
title: Intelli Credit Engine
emoji: 💳
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# Intelli-Credit Engine

A full-stack credit appraisal platform for hackathon demos.

It can:
- ingest company documents from local uploads
- extract 5-year financial signals
- generate synthetic GST/bank signals if data is missing
- run research + risk scoring
- produce CAM outputs (`pdf`, `tex`, `json`)

---

## Tech stack

- Backend: FastAPI (Python)
- Frontend: React + Vite
- Report generation: LaTeX + PDF compile
- Optional: Docker / Docker Compose
- Optional: Databricks-style bronze/silver/gold outputs

---

## Repository structure

- `src/` backend engine + API
- `frontend/` web app
- `scripts/` run scripts and utilities
- `data/input/` uploaded input documents
- `data/processed/` pipeline outputs
- `outputs/cam_reports/` generated CAM artifacts

---

## Prerequisites (local run without Docker)

- Python 3.11+
- Node.js 20+ and npm
- `pip`
- (Recommended) virtual environment

---

## 1) Backend setup

```bash
# from project root
python -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` in project root:

```env
API_PREFIX=/api/v1
ENGINE_STORAGE_ROOT=./runtime_data
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Start backend:

```bash
python run_api.py --host 0.0.0.0 --port 8001 --reload
```

Health check:

```bash
curl http://127.0.0.1:8001/api/v1/health
```

---

## 2) Frontend setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:
- `http://localhost:5173`

---

## 3) Running from another device on same Wi-Fi (LAN)

### Find your machine IP

Linux:
```bash
hostname -I
```

macOS:
```bash
ipconfig getifaddr en0
```

Windows (PowerShell):
```powershell
ipconfig
```
(Use the IPv4 address for your active network adapter.)

### Use that IP

If your IP is `192.168.1.50`:
- Frontend URL for teammate: `http://192.168.1.50:5173`
- Backend URL: `http://192.168.1.50:8001`

Set frontend API base (choose one):
- `frontend/.env.local`:
  ```env
  VITE_API_BASE_URL=http://192.168.1.50:8001/api/v1
  ```
- or `frontend/public/app-config.js`:
  ```js
  window.APP_CONFIG = { API_BASE_URL: "http://192.168.1.50:8001/api/v1" };
  ```

Also include LAN origin in backend CORS (project root `.env`):
```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.50:5173
```

Restart backend after env changes.

---

## 4) Docker run (recommended for consistency)

```bash
docker compose up --build
```

Open:
- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8001/api/v1/health`

Stop:
```bash
docker compose down
```

---

## 5) Using the app

1. Enter company name.
2. Upload available files by category.
3. Save credit officer inputs.
4. Run full evaluation.
5. Wait for completion.
6. Download CAM artifacts:
   - `CAM_report.pdf`
   - `CAM_report.tex`
   - `cam_payload.json`
   - `decision_trace.json`

---

## Environment variables

Project root `.env` (backend):
- `API_PREFIX` (default: `/api/v1`)
- `ENGINE_STORAGE_ROOT` (default: `./runtime_data`)
- `CORS_ORIGINS` (comma-separated allowed frontend origins)

Frontend:
- `VITE_API_BASE_URL` (optional explicit backend URL)

---

## Troubleshooting

### Backend unreachable from frontend
- Verify backend is running on `0.0.0.0:8001`
- Check `CORS_ORIGINS` includes frontend origin
- Confirm `VITE_API_BASE_URL` points to correct host/IP

### `Address already in use`
Use another port:
```bash
python run_api.py --host 0.0.0.0 --port 8002 --reload
```

### Upload fails with path errors
Set clean storage root:
```env
ENGINE_STORAGE_ROOT=./runtime_data
```
No extra spaces/newlines.

### Teammate cannot open your local app
- Both machines must be on same network
- Use your LAN IP (not `localhost`, not `0.0.0.0`)
- Allow ports `5173` and `8001` in firewall

---

## Security notes

- Do not commit secrets/tokens/API keys.
- Never share `.env` files publicly.
- Use `.env.example` with placeholders only.
- Keep personal paths/usernames out of configs and docs.
