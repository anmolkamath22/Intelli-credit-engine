"""PDF parsing utilities based on system pdftotext."""

from __future__ import annotations

import subprocess
from pathlib import Path


def extract_pdf_text(path: Path) -> str:
    """Extract text from PDF using pdftotext CLI."""
    try:
        result = subprocess.run(["pdftotext", str(path), "-"], check=False, capture_output=True, text=True)
        if result.returncode != 0:
            return ""
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
