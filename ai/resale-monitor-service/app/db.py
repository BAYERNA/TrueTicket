import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class Seller(Base):
    """FR-008: 상습 판매자 프로파일."""

    __tablename__ = "sellers"

    seller_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform_name: Mapped[str] = mapped_column(String(50))
    external_seller_id: Mapped[str] = mapped_column(String(100), index=True)
    listing_count: Mapped[int] = mapped_column(Integer, default=0)
    habitual_score: Mapped[float] = mapped_column(Float, default=0.0)


class ResaleListing(Base):
    """FR-006/FR-007: 크롤링된 재판매 게시물과 이상 가격 스코어."""

    __tablename__ = "resale_listings"

    listing_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey("sellers.seller_id"), index=True)
    platform_name: Mapped[str] = mapped_column(String(50))
    event_title_matched: Mapped[str] = mapped_column(String(255))
    listed_price: Mapped[float] = mapped_column(Float)
    price_anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


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
