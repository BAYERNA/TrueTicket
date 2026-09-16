import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class BehaviorLog(Base):
    """FR-003: 예매 화면 마우스 이동, 클릭 간격, 입력 속도 등 행동 로그."""

    __tablename__ = "behavior_logs"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reservation_session_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BotScore(Base):
    """FR-004: 취득 부정성 스코어(예매 세션 단위)."""

    __tablename__ = "bot_scores"

    score_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reservation_session_id: Mapped[str] = mapped_column(String(36), index=True)
    acquisition_fraud_score: Mapped[float] = mapped_column(Float)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


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
