from importlib.metadata import metadata
from confluent_kafka import Producer
import time
import json
import random
import logging
import uuid
from confluent_kafka.admin import AdminClient, NewTopic

KAFKA_BROKERS = "pkc-619z3.us-east1.gcp.confluent.cloud:9092"
NUM_PARTITIONS = 5
REPLICATION_FACTOR = 3
TOPIC_NAME = 'financial_transactions'
API_KEY = "VQQPMEBGHFUEJBJL"
API_SECRET = "OuBjm+YIYB/p846Su/ZQadTHMQCFppc/ve5Y+crraWKw+6hhET9BLitK+kdENLNd"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conf = {
    'bootstrap.servers': KAFKA_BROKERS,
    'queue.buffering.max.messages': 10000,
    'queue.buffering.max.kbytes': 51200,
    'batch.num.messages': 10,
    'linger.ms': 10,
    'acks': 1,
    'compression.type': 'gzip',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'PLAIN',
    'sasl.username': API_KEY,
    'sasl.password': API_SECRET
}

producer = Producer(conf)


def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery to Kafka topic failed due to {err}")
    else:
        print(f"{msg.key()} successfully produced")


def create_topic(topic_name):
    admin_client = AdminClient({
        "bootstrap.servers": KAFKA_BROKERS,
        "sasl.mechanisms": "PLAIN",
        "security.protocol": "SASL_SSL",
        "sasl.username": API_KEY,
        "sasl.password": API_SECRET
    })
    try:
        topic_metadata = admin_client.list_topics(timeout=10)
        if topic_name not in topic_metadata.topics:
            topic = NewTopic(
                topic=topic_name,
                num_partitions=NUM_PARTITIONS,
                replication_factor=REPLICATION_FACTOR,
                config={
                    "retention.ms": str(2 * 24 * 60 * 60 * 1000)  # 2 days in milliseconds
                }
            )
            fs = admin_client.create_topics([topic])
            for topic, future in fs.items():
                try:
                    future.result()
                    logging.info(f"Topic {topic_name} created successfully")
                except Exception as e:
                    logging.error(f"Failed to create topic {topic_name}: {e}")
        else:
            logger.info(f"Topic {topic_name} already exists")
    except Exception as e:
        logger.error(f"Error creating topic: {e}")


def generate_transaction():
    return dict(
        transaction_id=str(uuid.uuid4()),
        userId=f"user_{random.randint(1, 100)}",
        amount=round(random.uniform(50000, 150000), 2),
        transactionTime=int(time.time()),
        merchantId=random.choice(["merchant_1", "merchant_2"])
    )


if __name__ == "__main__":
    create_topic(TOPIC_NAME)

    while True:
        transaction = generate_transaction()
        try:
            producer.produce(
                topic=TOPIC_NAME,
                key=transaction['userId'],
                value=json.dumps(transaction).encode('utf-8'),
                on_delivery=delivery_report
            )
            producer.flush()

        except KeyboardInterrupt:
            producer.close()
        except Exception as e:
            logging.error(f"Error producing message: {e}")
            producer.close()

