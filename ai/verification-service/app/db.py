import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class VerificationLog(Base):
    """
    FR-010/FR-011/FR-011-1: 현장 검표 이력. 얼굴 캡처 원본 이미지는 DB가 아닌 MinIO에
    저장하고(v2 신규), 여기에는 참조 경로(snapshot_uri)만 남긴다.
    """

    __tablename__ = "verification_logs"

    verification_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reservation_id: Mapped[str] = mapped_column(String(36), index=True)
    qr_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    face_match_result: Mapped[bool] = mapped_column(Boolean)
    face_match_score: Mapped[float] = mapped_column(Float)
    snapshot_uri: Mapped[str] = mapped_column(String(500))
    duplicate_scan_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str] = mapped_column(String(100))


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
