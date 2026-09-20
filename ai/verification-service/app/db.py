import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Index, String, create_engine, text
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

    __table_args__ = (
        # FR-010/FR-011: 예매 건당 성공(face_match_result=true) 처리는 한 번만 있어야
        # 한다. 애플리케이션 레벨의 "먼저 조회하고 없으면 삽입" 체크만으로는 두 게이트에서
        # 같은 QR을 거의 동시에 스캔하는 경합을 막지 못한다 — DB 제약을 최종 방어선으로 둔다.
        Index(
            "idx_verification_logs_one_success_per_reservation",
            "reservation_id",
            unique=True,
            postgresql_where=text("face_match_result = true"),
        ),
    )


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
