from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, sum
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

KAFKA_BROKERS = "pkc-619z3.us-east1.gcp.confluent.cloud:9092"
SOURCE_TOPIC_NAME = 'financial_transactions'
API_KEY = "VQQPMEBGHFUEJBJL"
API_SECRET = "OuBjm+YIYB/p846Su/ZQadTHMQCFppc/ve5Y+crraWKw+6hhET9BLitK+kdENLNd"
TARGET_TOPIC = "aggregated_data"

spark = SparkSession.builder \
    .appName("Processing Kafka Stream Data") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5") \
    .getOrCreate()

# Define schema
transaction_schema = StructType([
    StructField("transaction_id", StringType(), True),
    StructField("userId", StringType(), True),
    StructField("amount", DoubleType(), True),  # Define as DoubleType
    StructField("transactionTime", StringType(), True),
    StructField("merchantId", StringType(), True)
])

kafka_config = {
    "kafka.bootstrap.servers": KAFKA_BROKERS,
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.sasl.jaas.config": f"org.apache.kafka.common.security.plain.PlainLoginModule required username='{API_KEY}' password='{API_SECRET}';"
}

# Read from Kafka
df = spark.readStream \
    .format("kafka") \
    .options(**kafka_config)\
    .option("subscribe", SOURCE_TOPIC_NAME) \
    .option("startingOffsets", "earliest") \
    .load()

# Parse Kafka messages
parsed_df = df.selectExpr("CAST(value AS STRING) as json_value") \
    .select(from_json(col("json_value"), transaction_schema).alias("data")) \
    .select("data.*")

# Group by userId and calculate total amount
aggregated_df = parsed_df.groupBy("userId").agg(sum("amount").alias("Total"))

# Write stream to Kafka
query = aggregated_df.selectExpr("CAST(userId AS STRING) AS key", "CAST(Total AS STRING) AS value") \
    .writeStream \
    .outputMode("update") \
    .format("kafka") \
    .options(**kafka_config) \
    .option("topic", TARGET_TOPIC) \
    .option("checkpointLocation", "/tmp/spark-checkpoints/financial_aggregations") \
    .start()

query.awaitTermination()
