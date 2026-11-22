from html import escape

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from ..adapters.resale_monitor import FEED_MARKER, MARKET_FEED_PATH
from ..models import MarketPost, NewMarketPost


router = APIRouter(tags=["market"])


@router.get("/api/market/posts")
def market_posts(request: Request, event_id: str | None = Query(default=None, max_length=64)) -> list[MarketPost]:
    return request.app.state.db.list_market_posts(event_id)


@router.post("/api/market/posts", status_code=status.HTTP_201_CREATED)
def add_market_post(request: Request, draft: NewMarketPost) -> MarketPost:
    post = request.app.state.db.create_market_post(draft)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "해당 가상 공연이 없습니다.")
    return post


def listing_html(post: MarketPost) -> str:
    price = f"{post.price:,}" if post.price is not None else ""
    return (
        f'<article class="listing" data-post-id="{escape(post.post_id)}" '
        f'data-event-id="{escape(post.event_id)}" data-channel="{escape(post.channel)}" '
        f'data-seller-id="{escape(post.author_handle)}" data-created-at="{escape(post.created_at)}">'
        f'<h2 class="title">{escape(post.title)}</h2>'
        f'<span class="price">{price}</span>'
        f'<div class="body">{escape(post.body)}</div>'
        '</article>'
    )


@router.get(MARKET_FEED_PATH, response_class=HTMLResponse)
def market_feed(request: Request, event_id: str | None = Query(default=None, max_length=64)) -> HTMLResponse:
    posts = request.app.state.db.list_market_posts(event_id)
    cards = "".join(listing_html(post) for post in posts)
    return HTMLResponse(
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<title>TicketGuard AI 가상 리셀 마켓 피드</title></head><body>'
        f'<main id="{FEED_MARKER}" data-count="{len(posts)}">{cards}</main></body></html>',
        headers={"Cache-Control": "no-store"},
    )
