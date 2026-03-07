# Databricks notebook source
"""03_research_enrichment

Reads Silver evidence and creates enriched tags for dashboard use.
"""

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

df = spark.table("silver.research_evidence")
enriched = (
    df
    .withColumn("has_litigation", F.lower(F.col("research_evidence_json")).contains("litigation"))
    .withColumn("has_news_risk", F.lower(F.col("research_evidence_json")).contains("controversy"))
)

enriched.write.mode("overwrite").format("delta").saveAsTable("silver.research_evidence")
print("Research evidence enriched")
