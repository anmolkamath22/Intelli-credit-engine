# Databricks notebook source
"""01_bronze_ingestion

Runs the core ingestion and writes Bronze payloads.
"""

# COMMAND ----------

import json

from scripts.run_pipeline import run

# COMMAND ----------

# DBTITLE 1,Widget input
# dbutils.widgets.text("company", "Blue Star Ltd")
# company = dbutils.widgets.get("company")
company = "Blue Star Ltd"

# COMMAND ----------

result = run(company, debug_financials=True)
print(json.dumps({"company": company, "bronze_written": result.get("databricks_table_writes", {})}, indent=2))

# COMMAND ----------

# Bronze sanity checks
for tbl in ["bronze.company_raw_files", "bronze.research_raw"]:
    try:
        display(spark.table(tbl).orderBy("company", ascending=True))
    except Exception as exc:
        print(f"Table {tbl} not available in Spark metastore: {exc}")
