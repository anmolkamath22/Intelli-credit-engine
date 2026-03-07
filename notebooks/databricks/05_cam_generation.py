# Databricks notebook source
"""05_cam_generation

Generates CAM payload/pdf and writes payload reference to Gold table.
"""

# COMMAND ----------

import json
from pathlib import Path

from scripts.run_pipeline import run

# dbutils.widgets.text("company", "Blue Star Ltd")
# company = dbutils.widgets.get("company")
company = "Blue Star Ltd"

result = run(company, debug_financials=False)
cam_payload_path = result.get("cam_payload")
cam_payload = json.loads(Path(cam_payload_path).read_text(encoding="utf-8")) if cam_payload_path else {}

spark.createDataFrame([
    {
        "company": company,
        "cam_payload_json": json.dumps(cam_payload),
        "cam_pdf_path": result.get("cam_pdf"),
    }
]).write.mode("append").format("delta").saveAsTable("gold.cam_payload")

print(json.dumps({"cam_pdf": result.get("cam_pdf"), "compile_success": result.get("cam_compile_success")}, indent=2))
