# Databricks Pipeline Notes

This project supports a Databricks-first bronze/silver/gold layout while reusing the existing Python engine modules.

## Table Contract

### Bronze
- `bronze.company_raw_files`: dataset presence and ingestion metadata
- `bronze.research_raw`: raw research summary references

### Silver
- `silver.financial_extraction`: normalized 5-year financial extraction payloads
- `silver.research_evidence`: structured evidence rows
- `silver.officer_inputs`: analyst qualitative inputs

### Gold
- `gold.credit_features`: engineered credit features
- `gold.credit_scores`: scoring outputs and calibrated bands
- `gold.cam_payload`: structured CAM content payload
- `gold.dashboard_credit_view`: dashboard-optimized table

## Notebook Orchestration
Run in this order:
1. `00_setup_environment.py`
2. `01_bronze_ingestion.py`
3. `02_silver_extraction.py`
4. `03_research_enrichment.py`
5. `04_gold_scoring.py`
6. `05_cam_generation.py`
7. `06_dashboard_tables.py`

## Local Fallback
If Spark/Databricks is unavailable, the same payloads are written as JSON under:
`data/databricks/<layer>/<table>/latest.json`

This keeps the architecture compatible while allowing local hackathon demos.
