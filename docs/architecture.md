# Architecture (Upgraded)

Pipeline flow:

`data/input -> dataset detection -> financial extraction -> synthetic GST/bank fallback -> circular-trading detection -> research agent -> officer inputs -> feature consolidation -> scoring -> decision trace -> CAM generation`

Key upgrades:
- unified `data/input` ingestion
- synthetic fallback for missing GST/bank datasets
- circular trading and revenue inflation detection
- explainable decision trace with evidence
- interactive CAM explainer (`ask_cam.py`)
