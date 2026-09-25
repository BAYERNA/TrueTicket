from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import Seller, get_db
from app.schemas import SellerProfileResponse

router = APIRouter(prefix="/api/resale-monitor", tags=["sellers"])


@router.get("/sellers/{seller_id}", response_model=SellerProfileResponse)
def get_seller_profile(seller_id: str, db: Session = Depends(get_db)) -> SellerProfileResponse:
    """SCR-09: 특정 판매자의 게시 이력과 상습성 지표."""
    seller = db.get(Seller, seller_id)
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    return SellerProfileResponse(
        seller_id=seller.seller_id,
        platform_name=seller.platform_name,
        external_seller_id=seller.external_seller_id,
        listing_count=seller.listing_count,
        habitual_score=seller.habitual_score,
    )
