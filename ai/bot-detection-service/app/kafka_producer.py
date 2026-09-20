import json
from kafka import KafkaProducer

from app.config import settings

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return _producer


def publish(topic: str, payload: dict) -> None:
    get_producer().send(topic, value=payload).get(timeout=10)
