"""PDF parsing utilities based on system pdftotext."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_pdf_text(path: str | Path) -> str:
    """Extract text from PDF using pdftotext or pdfplumber/PyMuPDF fallback."""
    try:
        # pdftotext is extremely fast and usually available via poppler-utils
        # Use -layout to preserve tabular row alignment, which is critical for financial statements
        result = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=False, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        return ""


def pdf_pages(path: Path) -> int:
    """Extract page count using pdfinfo CLI."""
    try:
        result = subprocess.run(["pdfinfo", str(path)], check=False, capture_output=True, text=True)
        if result.returncode != 0:
            return 0
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        return 0
    return 0
