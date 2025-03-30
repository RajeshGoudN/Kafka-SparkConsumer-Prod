from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

KAFKA_BROKERS = "pkc-619z3.us-east1.gcp.confluent.cloud:9092"
SOURCE_TOPIC_NAME = 'financial_transactions'
API_KEY = "VQQPMEBGHFUEJBJL"
API_SECRET = "OuBjm+YIYB/p846Su/ZQadTHMQCFppc/ve5Y+crraWKw+6hhET9BLitK+kdENLNd"
AGGREGATES_TOPIC = "transaction_aggregates"
ANOMALIES_TOPIC = "transaction_anomalies"
CHECKPOINT_DIR = "/mnt/spark-checkpoints"
STATES_DIR = "/mnt/spark-state"

spark=SparkSession.builder\
    .appName("processing kafka stream data")\
        .config("spark.jars.packages","org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5")\
        .config("spark.sql.streaming.checkpointLocation",CHECKPOINT_DIR)\
        .config("spark.sql.streaming.stateStore.stateStoreDir",STATES_DIR)\
        .config("spark.sql.shuffle.partitions", 20)\
        .getOrCreate()

#spark = SparkSession.builder \
#    .appName("processing kafka stream data") \
#    .config("spark.jars", "/path/to/spark-sql-kafka-0-10_2.13-3.5.5.jar") \
#    .getOrCreate() 

spark.sparkContext.setLogLevel("WARN")

transaction_schema=StructType([StructField("transaction_id",StringType(),True),\
                               StructField("userId",StringType(),True),\
                               StructField("amount",StringType(),True),\
                               StructField("transactionTime",StringType(),True),\
                               StructField("merchantId",StringType(),True)])

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKERS) \
    .option("kafka.security.protocol", "SASL_SSL") \
    .option("kafka.sasl.mechanism", "PLAIN") \
    .option(
        "kafka.sasl.jaas.config",
        f"org.apache.kafka.common.security.plain.PlainLoginModule required username='{API_KEY}' password='{API_SECRET}';"
    ) \
    .option("subscribe", "financial_transactions") \
    .option("startingOffsets","earliest")\
    .load()

transaction_df = df.selectExpr("CAST(value as STRING)")\
                    .select(from_json(col("value"),transaction_schema).alias("data")) \
                    .select("data.*")

query = transaction_df.writeStream \
    .format("console") \
    .outputMode("append") \
    .option("checkPointLocation",CHECKPOINT_DIR)\
    .start()

query.awaitTermination()


