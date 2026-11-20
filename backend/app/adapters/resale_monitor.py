from dataclasses import dataclass
from typing import Literal

import httpx
from bs4 import BeautifulSoup
from pydantic import ValidationError

from ..models import MarketPost


MARKET_FEED_PATH = "/api/market/feed"
FEED_MARKER = "trueticket-market-feed"


class FeedFormatError(ValueError):
    pass


@dataclass(frozen=True)
class CollectionResult:
    status: Literal["ok", "failed"]
    posts: tuple[MarketPost, ...] = ()
    error: str | None = None
    http_status: int | None = None


def parse_listings(html: str) -> tuple[MarketPost, ...]:
    soup = BeautifulSoup(html, "html.parser")
    feed = soup.find("main", id=FEED_MARKER)
    if feed is None:
        raise FeedFormatError("가상 마켓 피드 표시가 없습니다.")

    posts = []
    for card in feed.select(".listing"):
        title = card.select_one(".title")
        body = card.select_one(".body")
        if title is None or body is None:
            raise FeedFormatError("게시글 제목 또는 본문이 없습니다.")

        price_element = card.select_one(".price")
        price_text = price_element.get_text(strip=True).replace(",", "") if price_element else ""
        price = int(price_text) if price_text.isascii() and price_text.isdecimal() else None
        try:
            posts.append(MarketPost(
                post_id=card["data-post-id"],
                event_id=card["data-event-id"],
                channel=card["data-channel"],
                author_handle=card["data-seller-id"],
                created_at=card["data-created-at"],
                title=title.get_text(strip=True),
                body=body.get_text(),
                price=price,
            ))
        except (KeyError, ValidationError) as error:
            raise FeedFormatError("게시글에 필요한 식별 정보가 없거나 형식이 잘못됐습니다.") from error

    if str(len(posts)) != feed.get("data-count") or len({post.post_id for post in posts}) != len(posts):
        raise FeedFormatError("피드의 게시글 건수 또는 ID가 일치하지 않습니다.")
    return tuple(posts)


async def collect_posts(event_id: str | None = None, *, feed_port: int = 8000) -> CollectionResult:
    if not 1 <= feed_port <= 65535:
        raise ValueError("내부 피드 포트는 1~65535 범위여야 합니다.")
    params = {"event_id": event_id} if event_id is not None else None
    try:
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{feed_port}",
            timeout=10.0,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.get(MARKET_FEED_PATH, params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        return CollectionResult("failed", error="http_status", http_status=error.response.status_code)
    except httpx.RequestError:
        return CollectionResult("failed", error="connection_failed")

    try:
        posts = parse_listings(response.text)
    except FeedFormatError:
        return CollectionResult("failed", error="invalid_feed", http_status=response.status_code)
    return CollectionResult("ok", posts=posts, http_status=response.status_code)
