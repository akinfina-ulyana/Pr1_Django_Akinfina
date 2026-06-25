"""
A Kafka consumer acting as a management command.

It listens to the offers.created topic. For every message {"offer_id": N},
it dispatches the Celery task process_offer.delay(N).
The actual deduction of funds is performed by a Celery worker.
"""

import json
import logging
import signal

from django.conf import settings
from django.core.management.base import BaseCommand

from kafka import KafkaConsumer
from purchases.tasks import process_offer


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    It pulls tasks from Kafka and moves them to Redis; Celery then reads them from Redis.
    """

    help = "Listens to the topic - offers.created and initiates offer processing"

    def handle(self, *args, **options):
        self._ensure_topic_exists()
        self._running = True

        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)

        consumer = KafkaConsumer(
            settings.KAFKA_OFFER_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            consumer_timeout_ms=1000,
        )
        logger.info(
            "Offer consumer started. Topic=%s Group=%s", settings.KAFKA_OFFER_TOPIC, settings.KAFKA_CONSUMER_GROUP
        )

        try:
            while self._running:
                for message in consumer:
                    if not self._running:
                        break
                    self.handle_message(consumer, message)

        finally:
            consumer.close()
            logger.info("Offer consumer stopped", settings.KAFKA_CONSUMER_GROUP)

    def _ensure_topic_exists(self):
        from kafka.admin import KafkaAdminClient, NewTopic
        from kafka.errors import TopicAlreadyExistsError

        admin = KafkaAdminClient(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        topic = NewTopic(
            name=settings.KAFKA_OFFER_TOPIC,
            num_partitions=1,
            replication_factor=1,
        )
        try:
            admin.create_topics([topic])
            logger.info("Topic created: %s", settings.KAFKA_OFFER_TOPIC)
        except TopicAlreadyExistsError:
            logger.info("Topic already exists: %s", settings.KAFKA_OFFER_TOPIC)
        finally:
            admin.close()

    def handle_message(self, consumer, message):
        try:
            payload = message.value
            offer_id = payload.get("offer_id")

            if offer_id is None:
                logger.info("Message without offer_id, skipping: %s", payload)
                consumer.commit()
                return

            logger.info("Received offer_id=%s [partition=%s offset=%s]", offer_id, message.partition, message.offset)

            process_offer.delay(offer_id)

            consumer.commit()
            logger.info("Dispatched offer_id=%s to Celery and committed offset", offer_id)

        except Exception:
            logger.exception("Failed to handle message offset=%s", message.offset)

    def _stop(self, signum, frame):
        logger.info("Stop signal received (%s), shutting down...", signum)
        self._running = False
