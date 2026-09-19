import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def get_event_catalog() -> list[dict]:
    """
    크롤러가 게시물 제목(공연명)을 정가와 매칭하기 위해 ticket-service의 이벤트
    카탈로그를 조회한다. ticket-service가 응답하지 않으면 빈 목록을 반환해 크롤을
    건너뛰게 한다(이상 가격을 비교할 기준가가 없으면 점수를 매길 수 없다).
    """
    try:
        response = httpx.get(f"{settings.ticket_service_url}/api/events", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        logger.exception("ticket-service 이벤트 카탈로그 조회 실패")
        return []


def match_base_price(listing_title: str, events: list[dict]) -> float | None:
    """게시물 제목에 이벤트명이 포함되는지로 매칭한다(대소문자 무시, 단순 부분 문자열)."""
    normalized_title = listing_title.lower()
    for event in events:
        if event["title"].lower() in normalized_title:
            return float(event["basePrice"])
    return None
