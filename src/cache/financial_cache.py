"""Disk cache for parsed annual report text and extracted metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FinancialCache:
    """Simple JSON cache keyed by file signature (path + mtime + size)."""

    def __init__(self, cache_file: Path) -> None:
        self.cache_file = cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.cache_file.exists():
            return {}
        try:
            return json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self) -> None:
        self.cache_file.write_text(json.dumps(self._data, indent=2, ensure_ascii=True), encoding="utf-8")

    @staticmethod
    def _key(path: Path) -> str:
        st = path.stat()
        return f"{path.resolve()}::{int(st.st_mtime)}::{st.st_size}"

    def get(self, path: Path) -> dict[str, Any] | None:
        key = self._key(path)
        return self._data.get(key)

    def set(self, path: Path, payload: dict[str, Any]) -> None:
        key = self._key(path)
        self._data[key] = payload

