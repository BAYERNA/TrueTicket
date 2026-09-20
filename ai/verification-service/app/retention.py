import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal, VerificationLog
from app.minio_client import delete_snapshot

logger = logging.getLogger(__name__)


def purge_expired_snapshots() -> None:
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.snapshot_retention_days)
        logs = db.scalars(
            select(VerificationLog).where(
                VerificationLog.qr_scanned_at < cutoff,
                VerificationLog.snapshot_deleted_at.is_(None),
            ).limit(100)
        ).all()
        for log in logs:
            try:
                delete_snapshot(log.snapshot_uri)
                log.snapshot_uri = "deleted://retention"
                log.snapshot_deleted_at = datetime.now(timezone.utc)
            except Exception:
                logger.exception("snapshot retention failed: verification_id=%s", log.verification_id)
        db.commit()
    finally:
        db.close()
