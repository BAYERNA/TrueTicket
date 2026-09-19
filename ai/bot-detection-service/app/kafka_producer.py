import json
import logging
from datetime import datetime, timezone

from kafka import KafkaProducer
from kafka.errors import KafkaError

from app.config import settings

logger = logging.getLogger(__name__)

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return _producer


def publish_acquisition_score(reservation_session_id: str, score: float, is_flagged: bool) -> None:
    """AND 엔진(notification-service)이 구독하는 acquisition-fraud-scores 토픽에 발행한다."""
    event = {
        "reservationSessionId": reservation_session_id,
        "acquisitionFraudScore": score,
        "isFlagged": is_flagged,
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
    }
    try:
        get_producer().send("acquisition-fraud-scores", value=event)
    except KafkaError:
        logger.exception("Failed to publish acquisition score event for session=%s", reservation_session_id)
