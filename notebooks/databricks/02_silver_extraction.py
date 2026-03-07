# Databricks notebook source
"""02_silver_extraction

Materializes Silver extraction and evidence tables.
"""

# COMMAND ----------

# dbutils.widgets.text("company", "Blue Star Ltd")
# company = dbutils.widgets.get("company")
company = "Blue Star Ltd"

# COMMAND ----------

from pathlib import Path
import json

from src.utils.text_processing import slugify

ROOT = Path.cwd()
slug = slugify(company)
proc = ROOT / "data" / "processed" / slug

financial_history = json.loads((proc / "financial_history.json").read_text(encoding="utf-8"))
research_evidence = json.loads((proc / "research_evidence.json").read_text(encoding="utf-8"))

df_fin = spark.createDataFrame([
    {
        "company": company,
        "financial_history_json": json.dumps(financial_history),
        "source": str(proc / "financial_history.json"),
    }
])
df_res = spark.createDataFrame([
    {
        "company": company,
        "research_evidence_json": json.dumps(research_evidence),
        "source": str(proc / "research_evidence.json"),
    }
])

df_fin.write.mode("append").format("delta").saveAsTable("silver.financial_extraction")
df_res.write.mode("append").format("delta").saveAsTable("silver.research_evidence")

print("Silver tables updated")
