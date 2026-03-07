# Databricks notebook source
"""00_setup_environment

Initializes Databricks runtime for intelli-credit-engine pipeline.
"""

# COMMAND ----------

# DBTITLE 1,Install project dependencies (optional)
# %pip install -r /Workspace/Repos/<user>/intelli-credit-engine/requirements.txt

# COMMAND ----------

from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
print("Spark version:", spark.version)

# COMMAND ----------

BRONZE_TABLES = [
    "bronze.company_raw_files",
    "bronze.research_raw",
]
SILVER_TABLES = [
    "silver.financial_extraction",
    "silver.research_evidence",
    "silver.officer_inputs",
]
GOLD_TABLES = [
    "gold.credit_features",
    "gold.credit_scores",
    "gold.cam_payload",
]
print({"bronze": BRONZE_TABLES, "silver": SILVER_TABLES, "gold": GOLD_TABLES})
