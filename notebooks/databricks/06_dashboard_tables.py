# Databricks notebook source
"""06_dashboard_tables

Creates a compact dashboard table from Gold layer outputs.
"""

# COMMAND ----------

from pyspark.sql import functions as F

features = spark.table("gold.credit_features").withColumnRenamed("payload", "features_payload")
scores = spark.table("gold.credit_scores").withColumnRenamed("payload", "score_payload")
cam = spark.table("gold.cam_payload")

dashboard = (
    features.alias("f")
    .join(scores.alias("s"), on="company", how="left")
    .join(cam.alias("c"), on="company", how="left")
    .withColumn("updated_at", F.current_timestamp())
)

dashboard.write.mode("overwrite").format("delta").saveAsTable("gold.dashboard_credit_view")
print("Table ready: gold.dashboard_credit_view")
