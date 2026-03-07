"""Extract current board/director names from local company documents."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.ingestion.pdf_parser import extract_pdf_text
from src.utils.file_loader import list_files
from src.utils.text_processing import clean_text


DIRECTOR_PATTERNS = [
    r"\bMr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b",
    r"\bMs\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b",
    r"\bMrs\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b",
    r"\bDr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b",
]


def extract_board_of_directors(company_dir: Path) -> list[str]:
    """Extract likely board names from annual-report and profile documents."""
    files = []
    for d in [company_dir / "annual_reports", company_dir / "management", company_dir / "identity"]:
        if d.exists():
            files.extend(list_files(d))
    # Use processed document cache if available.
    proc_docs = company_dir.parents[1] / "processed" / company_dir.name / "documents.json"
    if proc_docs.exists():
        files.append(proc_docs)

    names: list[str] = []
    for f in files:
        text = ""
        try:
            if f.suffix.lower() == ".pdf":
                text = clean_text(extract_pdf_text(f))
            elif f.suffix.lower() == ".json":
                payload = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(payload, list):
                    text = clean_text(" ".join(str(x.get("text", "")) for x in payload if isinstance(x, dict)))
                elif isinstance(payload, dict):
                    text = clean_text(json.dumps(payload))
            else:
                text = clean_text(f.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            text = ""
        if not text:
            continue
        for pat in DIRECTOR_PATTERNS:
            for m in re.findall(pat, text):
                name = re.sub(r"\s+", " ", m).strip()
                if name not in names:
                    names.append(name)
    # Keep a compact top list to avoid noisy extraction.
    return names[:15]
