# Intelli-Credit-Engine

Production-style hackathon project for automated **corporate credit appraisal**.

The engine ingests multi-source company data (financial + legal + behavioral), builds risk signals, computes an explainable credit score, and generates a professional **Credit Appraisal Memo (CAM)**.

## Project Objective
- Handle incomplete real-world datasets.
- Perform 5-year financial analysis from annual reports.
- Generate synthetic fallback signals when datasets are missing.
- Produce an explainable credit decision with evidence-backed CAM output.

## What This Project Consumes
This project is not limited to annual reports. It can consume:
- GST returns and compliance inputs
- Annual reports (5-year preferred)
- Financial statements
- Balance sheets
- Bank statements
- Litigation and legal documents
- News/risk intelligence documents
- Qualitative or analyst-provided notes (if available)

If users provide only a subset of these files, the pipeline still runs end-to-end and fills missing parts using synthetic GST/bank behavior models.

## Approach
1. Data ingestion and detection
- Reads company datasets from `data/input/<company_slug>/`.
- Detects available sources (annual reports, GST, balance sheets, financial statements, bank statements, legal/litigation docs, news/risk docs).

2. Financial extraction (5-year)
- Parses annual reports year-wise.
- Normalizes values to **INR Crores**.
- Runs sanity checks and auto-correction for unrealistic values.
- Builds `financial_history.json` and `financial_trends.json`.

3. Risk intelligence
- Research agent derives promoter/legal/news/sector signals.
- Circular-trading detector checks GST vs bank inflow mismatch and flow loops.
- Synthetic GST/bank signals are generated when raw files are missing.

### Why this is robust for hackathons
- Real-world datasets are often incomplete.
- This engine supports partial uploads and still generates complete appraisal outputs.
- Missing data does not break the pipeline; it triggers controlled synthetic fallback generation.

4. Scoring and recommendation
- Consolidates features into `credit_features.json`.
- Computes credit score, loan recommendation, and interest rate.
- Decision trace captures risk flags and feature contributions.

5. CAM generation
- Produces narrative CAM (PDF + TXT/DOCX fallback).
- Includes source attribution by dataset type (not hardcoded absolute machine paths).

## Tech Stack
- Python 3.10+
- Pandas / NumPy
- YAML (`PyYAML`)
- PDF tools (`pdftotext`, `pdfinfo`)
- `python-docx` (DOCX export fallback)
- Lightweight in-repo vector retrieval (RAG-style chunk retrieval)

## Repository Structure
```text
intelli-credit-engine/
  configs/
  data/
    input/
    processed/
  outputs/
    cam_reports/
  scripts/
  src/
    ingestion/
    validation/
    synthetic/
    research/
    credit_model/
    cam/
    assistant/
    vector_store/
  run_pipeline.py
  ask_cam.py
```

## Input Data Contract
Place files under:

`data/input/<company_slug>/`
- `annual_reports/` (prefer 5 years: FY20..FY24/FY25 PDFs)
- `financial_statements/`
- `balance_sheets/`
- `gst_returns/`
- `bank_statements/`
- `legal_documents/`
- `news_documents/`

If a dataset is missing, synthetic fallback is used where supported (especially GST and bank behavior), so CAM generation can still complete.

## Setup
```bash
cd "intelli-credit-engine"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

System dependency for PDF extraction:
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

## Run Commands
Run full pipeline:
```bash
python run_pipeline.py --company "Blue Star Ltd"
```

Ask CAM explainer questions:
```bash
python ask_cam.py --company "Blue Star Ltd"
```

Sync input links from precursor dataset repo:
```bash
./scripts/sync_input_links.sh
```

## Outputs
Per company in `data/processed/<company_slug>/`:
- `financial_features.json`
- `financial_history.json`
- `financial_trends.json`
- `synthetic_gst_features.json`
- `synthetic_bank_features.json`
- `research_summary.json`
- `credit_features.json`
- `decision_trace.json`
- `scoring_output.json`

CAM reports:
- `outputs/cam_reports/<company_slug>/CAM_report.pdf`
- `outputs/cam_reports/<company_slug>/CAM_report.txt` (or `.docx` when available)

## CAM Contents
- Executive Summary
- Company Overview
- 5-Year Financial Performance
- Financial Ratio Table (INR Crores)
- Financial Trend Analysis
- Promoter & Management Assessment
- Industry Outlook
- Litigation Profile
- Risk Flags + Decision Logic
- Final Credit Score
- Recommended Loan Limit
- Interest Rate Recommendation
- Supporting Evidence + Source Attribution


