import logging

import httpx

logger = logging.getLogger(__name__)


def fetch_html(url: str) -> str | None:
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError:
        logger.exception("크롤 대상 페이지 조회 실패: %s", url)
        return None
