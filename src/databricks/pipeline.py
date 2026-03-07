"""Databricks Bronze/Silver/Gold writer with local fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TABLE_PATHS = {
    "bronze.company_raw_files": "bronze/company_raw_files",
    "bronze.research_raw": "bronze/research_raw",
    "silver.financial_extraction": "silver/financial_extraction",
    "silver.research_evidence": "silver/research_evidence",
    "silver.officer_inputs": "silver/officer_inputs",
    "gold.credit_features": "gold/credit_features",
    "gold.credit_scores": "gold/credit_scores",
    "gold.cam_payload": "gold/cam_payload",
}


def write_table_local(base_dir: Path, table_name: str, payload: dict[str, Any]) -> str:
    """Write table payload as local JSON fallback."""
    rel = TABLE_PATHS.get(table_name, table_name.replace(".", "/"))
    out_dir = base_dir / rel
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "latest.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return str(out_file)


def write_table_spark(spark: Any, table_name: str, payload: dict[str, Any], mode: str = "append") -> None:
    """Write payload to Databricks table using Spark when available."""
    df = spark.createDataFrame([payload])  # type: ignore[attr-defined]
    df.write.mode(mode).format("delta").saveAsTable(table_name)


def write_databricks_tables(
    payloads: dict[str, dict[str, Any]],
    spark: Any | None = None,
    local_base_dir: Path | None = None,
) -> dict[str, str]:
    """Write Bronze/Silver/Gold payloads to Spark tables or local fallback."""
    local_base_dir = local_base_dir or Path("data/databricks")
    written: dict[str, str] = {}
    for table_name, payload in payloads.items():
        if spark is not None:
            try:
                write_table_spark(spark, table_name, payload, mode="append")
                written[table_name] = "spark_table"
                continue
            except Exception:
                pass
        written[table_name] = write_table_local(local_base_dir, table_name, payload)
    return written

