"""Manual credit officer qualitative input loader."""

from __future__ import annotations

import json
from pathlib import Path


def load_officer_inputs(path: Path) -> dict:
    """Load officer input JSON; return defaults if missing."""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {
        "factory_utilization": 0.6,
        "management_credibility": 0.6,
        "inventory_build_up": 0.4,
        "supply_chain_risk": 0.4,
    }
