from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import ResaleListing, get_db
from app.listing_service import ingest_listing
from app.schemas import IngestListingRequest, ListingResponse

router = APIRouter(prefix="/api/resale-monitor", tags=["listings"])


@router.post("/listings", response_model=ListingResponse, status_code=201)
def create_listing(request: IngestListingRequest, db: Session = Depends(get_db)) -> ListingResponse:
    """FR-006/007/008/009: 크롤러가 수집한(또는 수동 제출된) 게시물을 적재하고 스코어를 산출한다."""
    return ingest_listing(request, db)


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
