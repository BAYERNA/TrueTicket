"""
FR-006: 리셀 플랫폼 크롤링 MVP.

실제 서비스 대상 플랫폼(중고나라·번개장터·티켓베이 등)은 배포 시 CRAWL_SOURCE_URL로
설정한다. 각 플랫폼마다 HTML 구조가 다르므로, 정식 버전에서는 플랫폼별 파서를
추가해야 한다 — 지금은 다음 최소 계약을 따르는 리스팅 페이지 하나를 파싱한다:

    <div class="listing" data-seller-id="...">
      <span class="title">...</span>
      <span class="price">...</span>
    </div>

MVP 범위상 제3자 사이트에 대한 실제 스크래핑 대상/셀렉터는 포함하지 않았고,
이 구조를 따르는 소스에 붙이면 바로 동작하도록 파서·정가 매칭·적재 파이프라인만
구현했다.
"""

import logging

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.crawler_client import fetch_html
from app.listing_service import ingest_listing
from app.schemas import IngestListingRequest
from app.ticket_client import get_event_catalog, match_base_price

logger = logging.getLogger(__name__)


def parse_listings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select(".listing"):
        title_el = card.select_one(".title")
        price_el = card.select_one(".price")
        seller_id = card.get("data-seller-id")
        if title_el is None or price_el is None or not seller_id:
            continue
        try:
            price = float(price_el.get_text(strip=True).replace(",", ""))
        except ValueError:
            logger.warning("가격 파싱 실패, 항목 건너뜀: %r", price_el.get_text(strip=True))
            continue
        items.append({"title": title_el.get_text(strip=True), "price": price, "seller_id": str(seller_id)})
    return items


def run_crawl_once(db: Session) -> dict:
    """소스 1개를 1회 크롤링하고 매칭/적재 결과를 요약해 반환한다."""
    if not settings.crawl_source_url:
        return {"skipped": "CRAWL_SOURCE_URL not configured"}

    html = fetch_html(settings.crawl_source_url)
    if html is None:
        return {"fetched": 0, "matched": 0, "ingested": 0, "error": "fetch failed"}

    raw_items = parse_listings(html)
    events = get_event_catalog()

    ingested = 0
    unmatched = 0
    for item in raw_items:
        base_price = match_base_price(item["title"], events)
        if base_price is None:
            unmatched += 1
            continue

        ingest_listing(
            IngestListingRequest(
                platform_name=settings.crawl_source_platform_name,
                external_seller_id=item["seller_id"],
                event_title=item["title"],
                listed_price=item["price"],
                base_price=base_price,
            ),
            db,
        )
        ingested += 1

    logger.info(
        "크롤 완료: fetched=%d matched=%d unmatched=%d", len(raw_items), ingested, unmatched
    )
    return {"fetched": len(raw_items), "matched": ingested, "unmatched": unmatched}
