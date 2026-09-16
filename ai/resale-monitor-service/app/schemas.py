from pydantic import BaseModel


class IngestListingRequest(BaseModel):
    """
    크롤러(FR-006)가 수집한 재판매 게시물 원본. base_price는 리셀 플랫폼 크롤러가
    ticket-service의 이벤트 카탈로그(공연명 기준)와 매칭해 채워 넣는다. 예매 직후
    재판매된 특정 티켓임을 식별할 수 있는 경우에만 reservation_session_id를 채운다
    (AND 엔진 조인 키).
    """

    platform_name: str
    external_seller_id: str
    event_title: str
    listed_price: float
    base_price: float
    reservation_session_id: str | None = None


class ListingResponse(BaseModel):
    listing_id: str
    seller_id: str
    platform_name: str
    event_title_matched: str
    listed_price: float
    price_anomaly_score: float


class SellerProfileResponse(BaseModel):
    seller_id: str
    platform_name: str
    external_seller_id: str
    listing_count: int
    habitual_score: float
