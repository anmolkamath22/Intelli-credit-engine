# Intelli Credit Engine

Intelli Credit Engine is a hackathon-ready AI credit appraisal platform that ingests multi-source company data, computes risk features, produces calibrated credit decisions, and generates a professional CAM report (`.tex` + `.pdf`).

---

## 1) What This Project Does

- Ingests company data from local folder inputs.
- Extracts and validates 5-year financial history from annual reports.
- Normalizes units to INR Crores.
- Generates synthetic GST and bank signals when data is missing.
- Runs research intelligence (news, litigation, board/director context).
- Builds explainable credit score + decision trace.
- Generates CAM using deterministic flow: `JSON -> LaTeX -> PDF`.
- Exposes backend APIs and a frontend dashboard for uploads, execution, and downloads.
- Supports Databricks-compatible Bronze/Silver/Gold persistence.

---

## 2) Repository Structure

```text
intelli-credit-engine/
  configs/
  data/
    input/
    processed/
    databricks/
  docs/
  frontend/
  notebooks/databricks/
  outputs/
    cam_reports/
    debug/
  scripts/
  src/
    api/
    ingestion/
    research/
    credit_model/
    cam/
    databricks/
    validation/
    synthetic/
  run_pipeline.py
  run_api.py
  requirements.txt
```

---

## 3) Input Data Contract

Place company files in:

`data/input/<company_slug>/`

Supported folders:
- `annual_reports/`
- `financial_statements/`
- `balance_sheets/`
- `gst_returns/`
- `bank_statements/`
- `legal_documents/`
- `news_documents/`
- `qualitative/` (optional officer input JSON)

### File Format Guidance
- `annual_reports`: PDF preferred (best supported)
- `financial_statements` / `balance_sheets`: PDF / JSON / CSV supported
- `gst_returns`: JSON/CSV preferred
- `bank_statements`: CSV preferred
- `legal_documents` / `news_documents`: TXT/JSON/PDF accepted (text quality depends on source)

If private data is missing, synthetic fallback is used for GST/bank signals.

---

## 4) Scoring Bands

- `75-100`: Strong Credit
- `60-74`: Acceptable / Moderate Risk
- `45-59`: Weak / Elevated Risk
- `<45`: High Risk

Loan recommendation and interest are calibrated from score + risk features.

---

## 5) CAM Generation

CAM pipeline is deterministic and safe:

1. Build structured `cam_payload.json`
2. Render LaTeX via fixed template
3. Compile with local compiler (`tectonic` -> `xelatex` -> `pdflatex`)

Outputs:
- `CAM_report.pdf`
- `CAM_report.tex`
- `cam_payload.json`
- `compile.log`

---

## 6) Databricks Compatibility

### Bronze
- `bronze.company_raw_files`
- `bronze.research_raw`

### Silver
- `silver.financial_extraction`
- `silver.research_evidence`
- `silver.officer_inputs`

### Gold
- `gold.credit_features`
- `gold.credit_scores`
- `gold.cam_payload`
- `gold.dashboard_credit_view`

Notebooks available in `notebooks/databricks/`:
1. `00_setup_environment.py`
2. `01_bronze_ingestion.py`
3. `02_silver_extraction.py`
4. `03_research_enrichment.py`
5. `04_gold_scoring.py`
6. `05_cam_generation.py`
7. `06_dashboard_tables.py`

---

## 7) Full Local Setup (Start to End)

## 7.1 Python environment

```bash
cd "/home/anmol_kamath/Credit Evaluator Hackathon/intelli-credit-engine"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 7.2 System dependencies

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils texlive-latex-base texlive-latex-recommended texlive-fonts-recommended nodejs npm
```

## 7.3 Run pipeline once (CLI)

```bash
python run_pipeline.py --company "Blue Star Ltd" --debug-financials
```

## 7.4 Run backend API (Terminal 1)

```bash
cd "/home/anmol_kamath/Credit Evaluator Hackathon/intelli-credit-engine"
source .venv/bin/activate
python run_api.py --host 0.0.0.0 --port 8001 --reload
```

## 7.5 Run frontend (Terminal 2)

```bash
cd "/home/anmol_kamath/Credit Evaluator Hackathon/intelli-credit-engine/frontend"
VITE_API_BASE=http://localhost:8001 npm install
VITE_API_BASE=http://localhost:8001 npm run dev
```

## 7.6 Open in browser

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8001/docs`

---

## 8) Frontend Flow

1. Enter company name.
2. Upload files by dataset type.
3. Save officer inputs.
4. Click **Run Full Credit Evaluation**.
5. Review score, trends, risk breakdown, board/litigation/news findings.
6. Download CAM artifacts.

---

## 9) API Endpoints

- `GET /api/v1/health`
- `GET /api/v1/companies`
- `POST /api/v1/company/upload`
- `POST /api/v1/company/officer-inputs`
- `POST /api/v1/pipeline/run`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/financials/{company}`
- `GET /api/v1/research/{company}`
- `GET /api/v1/scores/{company}`
- `GET /api/v1/dashboard/{company}`
- `GET /api/v1/download/{company}/{artifact}`

Download artifacts:
- `cam_pdf`
- `cam_tex`
- `cam_payload`
- `decision_trace`
- `score_audit`

---

## 10) Key Outputs

Per company (`data/processed/<company_slug>/`):
- `financial_history.json`
- `financial_trends.json`
- `validated_financials.json`
- `financial_features.json`
- `credit_features.json`
- `research_summary.json`
- `research_evidence.json`
- `scoring_output.json`
- `decision_trace.json`
- `pipeline_output.json`

CAM outputs (`outputs/cam_reports/<company_slug>/`):
- `CAM_report.pdf`
- `CAM_report.tex`
- `cam_payload.json`
- `compile.log`

Debug outputs (`outputs/debug/`):
- `financial_audit_report.json`
- `score_audit_<company>.json`
- `unit_detection_<company>.json`
- `financial_anomalies_<company>.json`

---

## 11) Troubleshooting

### PDF download says artifact not found
- Re-run evaluation once.
- Ensure `cam_compile_success` is true in `pipeline_output.json`.

### Port already in use
- Change backend port:
```bash
python run_api.py --host 0.0.0.0 --port 8002 --reload
```
- Start frontend with matching API base:
```bash
VITE_API_BASE=http://localhost:8002 npm run dev
```

### Frontend still shows old values
- Hard refresh browser (`Ctrl+Shift+R`).
- Click `Refresh Results`.

---

## 12) Hackathon Positioning

This project is designed as a production-style prototype:
- deterministic ingestion first
- synthetic completion for missing private data
- explainable scoring and decision trace
- evidence-backed CAM outputs
- Databricks-compatible architecture
- deployable API + dashboard demo

