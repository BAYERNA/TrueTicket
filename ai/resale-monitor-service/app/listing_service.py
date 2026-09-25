from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import OutboxEvent, ResaleListing, Seller
from app.schemas import IngestListingRequest, ListingResponse
from app.scoring import (
    compute_habitual_score,
    compute_price_anomaly_score,
    compute_seller_repetition_score,
)
from app.model_metrics import flagged_counter, score_histogram


def ingest_listing(request: IngestListingRequest, db: Session) -> ListingResponse:
    """
    FR-006/007/008/009: 게시물을 적재하고 상습 판매 스코어를 산출한다.
    HTTP 라우터(POST /listings, 수동/외부 제출)와 크롤러(app/crawler.py, 주기 배치) 양쪽에서
    공유하는 단일 진입점이다.
    """
    seller = db.scalar(
        select(Seller).where(
            Seller.platform_name == request.platform_name,
            Seller.external_seller_id == request.external_seller_id,
        )
    )
    if seller is None:
        seller = Seller(
            platform_name=request.platform_name,
            external_seller_id=request.external_seller_id,
            listing_count=0,
        )
        db.add(seller)
        db.flush()

    seller.listing_count += 1

    price_anomaly_score = compute_price_anomaly_score(request.listed_price, request.base_price)
    seller_repetition_score = compute_seller_repetition_score(seller.listing_count)
    seller.habitual_score = compute_habitual_score(price_anomaly_score, seller_repetition_score)

    listing = ResaleListing(
        seller_id=seller.seller_id,
        platform_name=request.platform_name,
        event_title_matched=request.event_title,
        listed_price=request.listed_price,
        price_anomaly_score=price_anomaly_score,
        model_version=settings.model_version,
    )
    db.add(listing)
    db.flush()

    if request.reservation_session_id:
        is_flagged = seller.habitual_score >= settings.habitual_score_threshold
        score_histogram.observe(seller.habitual_score)
        if is_flagged:
            flagged_counter.labels(settings.model_version).inc()
        db.add(OutboxEvent(topic="habitual-resale-scores", payload={
            "reservationSessionId": request.reservation_session_id,
            "listingId": listing.listing_id,
            "habitualScore": seller.habitual_score,
            "isFlagged": is_flagged,
            "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        }))

    db.commit()
    db.refresh(listing)

    return ListingResponse(
        listing_id=listing.listing_id,
        seller_id=seller.seller_id,
        platform_name=listing.platform_name,
        event_title_matched=listing.event_title_matched,
        listed_price=listing.listed_price,
        price_anomaly_score=listing.price_anomaly_score,
    )
