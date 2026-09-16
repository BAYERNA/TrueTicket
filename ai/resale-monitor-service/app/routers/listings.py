from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import ResaleListing, Seller, get_db
from app.kafka_producer import publish_habitual_score
from app.schemas import IngestListingRequest, ListingResponse
from app.scoring import (
    compute_habitual_score,
    compute_price_anomaly_score,
    compute_seller_repetition_score,
)

router = APIRouter(prefix="/api/resale-monitor", tags=["listings"])


@router.post("/listings", response_model=ListingResponse, status_code=201)
def ingest_listing(request: IngestListingRequest, db: Session = Depends(get_db)) -> ListingResponse:
    """FR-006/007/008/009: 크롤러가 수집한 게시물을 적재하고 상습 판매 스코어를 산출한다."""
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
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    if request.reservation_session_id:
        is_flagged = seller.habitual_score >= settings.habitual_score_threshold
        publish_habitual_score(
            reservation_session_id=request.reservation_session_id,
            listing_id=listing.listing_id,
            score=seller.habitual_score,
            is_flagged=is_flagged,
        )

    return ListingResponse(
        listing_id=listing.listing_id,
        seller_id=seller.seller_id,
        platform_name=listing.platform_name,
        event_title_matched=listing.event_title_matched,
        listed_price=listing.listed_price,
        price_anomaly_score=listing.price_anomaly_score,
    )


@router.get("/listings/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: str, db: Session = Depends(get_db)) -> ListingResponse:
    """SCR-08 이상거래 상세 판정 화면에서 게시물 단건을 조회한다."""
    listing = db.get(ResaleListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    return ListingResponse(
        listing_id=listing.listing_id,
        seller_id=listing.seller_id,
        platform_name=listing.platform_name,
        event_title_matched=listing.event_title_matched,
        listed_price=listing.listed_price,
        price_anomaly_score=listing.price_anomaly_score,
    )


@router.get("/listings", response_model=list[ListingResponse])
def list_listings(db: Session = Depends(get_db)) -> list[ListingResponse]:
    """SCR-07 재판매 모니터링 대시보드용 목록 조회."""
    listings = db.scalars(select(ResaleListing).order_by(ResaleListing.collected_at.desc()).limit(200)).all()
    return [
        ListingResponse(
            listing_id=l.listing_id,
            seller_id=l.seller_id,
            platform_name=l.platform_name,
            event_title_matched=l.event_title_matched,
            listed_price=l.listed_price,
            price_anomaly_score=l.price_anomaly_score,
        )
        for l in listings
    ]
