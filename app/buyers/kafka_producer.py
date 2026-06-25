import json
import logging

from django.conf import settings

from kafka import KafkaProducer


logger = logging.getLogger(__name__)

producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global producer
    if producer is None:
        producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
            acks="all",
            retries=3,
        )
        logger.info("Kafka producer created: %s", settings.KAFKA_BOOTSTRAP_SERVERS)
    return producer


def publish_event(topic: str, key, value: dict) -> None:
    producer = get_producer()
    future = producer.send(topic, key=key, value=value)

    producer.flush()
    try:
        record_metadata = future.get(timeout=10)
        logger.info(
            "Published to %s [partition=%s offset=%s] key=%s",
            topic,
            record_metadata.partition,
            record_metadata.offset,
            key,
        )
    except Exception:
        logger.exception("Failed to publish event to %s key=%s", topic, key)
        raise
