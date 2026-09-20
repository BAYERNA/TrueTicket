import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import OutboxEvent, SessionLocal
from app.kafka_producer import publish

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


def dispatch_outbox() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        events = db.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.status.in_(["PENDING", "FAILED"]), OutboxEvent.next_attempt_at <= now)
            .order_by(OutboxEvent.created_at).limit(50).with_for_update(skip_locked=True)
        ).all()
        for event in events:
            try:
                publish(event.topic, event.payload)
                event.status, event.published_at, event.last_error = "SENT", now, None
            except Exception as exc:
                event.attempts += 1
                event.status = "DEAD" if event.attempts >= MAX_ATTEMPTS else "FAILED"
                event.last_error = str(exc)[:2000]
                event.next_attempt_at = now + timedelta(seconds=min(2 ** event.attempts, 300))
                logger.exception("outbox publish failed: event_id=%s", event.event_id)
        db.commit()
    finally:
        db.close()
