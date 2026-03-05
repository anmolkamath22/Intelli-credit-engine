"""Local litigation lookup from provided legal docs."""

from __future__ import annotations

import json
from pathlib import Path

from src.utils.file_loader import list_files, read_json
from src.utils.text_processing import clean_text


def lookup_litigation(company_dir: Path) -> dict:
    """Estimate litigation risk from local legal documents."""
    legal_dir_candidates = [company_dir / "legal_documents", company_dir / "litigation_docs", company_dir / "legal"]
    files = []
    for d in legal_dir_candidates:
        if d.exists():
            files.extend(list_files(d))

    case_count = 0
    insolvency_flag = 0
    summaries: list[str] = []

    for f in files:
        if f.suffix.lower() == ".json":
            payload = read_json(f)
            if payload:
                case_count += int(payload.get("case_count", 0) or 0)
                insolvency_flag = max(insolvency_flag, int(bool(payload.get("insolvency_flag", False))))
                summaries.append(str(payload)[:300])
        else:
            try:
                txt = clean_text(f.read_text(encoding="utf-8", errors="ignore")).lower()
                case_count += txt.count("case") + txt.count("petition")
                insolvency_flag = max(insolvency_flag, int("insolvency" in txt or "nclt" in txt))
                summaries.append(txt[:300])
            except Exception:
                continue

    risk = min(100.0, case_count * 4 + insolvency_flag * 25)
    return {
        "litigation_count": int(case_count),
        "litigation_risk_score": round(float(risk), 2),
        "insolvency_flag": int(insolvency_flag),
        "case_summary": summaries[:5],
    }
