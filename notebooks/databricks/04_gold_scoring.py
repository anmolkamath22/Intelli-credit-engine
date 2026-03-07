# Databricks notebook source
"""04_gold_scoring

Moves processed scoring/feature artifacts to Gold Delta tables.
"""

# COMMAND ----------

import json
from pathlib import Path

from src.utils.text_processing import slugify

# dbutils.widgets.text("company", "Blue Star Ltd")
# company = dbutils.widgets.get("company")
company = "Blue Star Ltd"
slug = slugify(company)
ROOT = Path.cwd()
proc = ROOT / "data" / "processed" / slug

features = json.loads((proc / "credit_features.json").read_text(encoding="utf-8"))
score = json.loads((proc / "scoring_output.json").read_text(encoding="utf-8"))

spark.createDataFrame([{"company": company, "payload": json.dumps(features)}]).write.mode("append").format("delta").saveAsTable("gold.credit_features")
spark.createDataFrame([{"company": company, "payload": json.dumps(score)}]).write.mode("append").format("delta").saveAsTable("gold.credit_scores")
print("Gold features/scores updated")
