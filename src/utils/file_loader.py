"""File loading helpers with format detection."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def read_json(path: Path) -> dict:
    """Read JSON file as dict; return empty dict on failure."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_csv(path: Path) -> pd.DataFrame:
    """Read CSV file with pandas."""
    return pd.read_csv(path)


def list_files(root: Path, exts: set[str] | None = None) -> list[Path]:
    """List files recursively from root, optionally filtering by suffix."""
    if not root.exists():
        return []
    files = [p for p in root.rglob("*") if p.is_file()]
    if exts is None:
        return sorted(files)
    return sorted([p for p in files if p.suffix.lower() in exts])
