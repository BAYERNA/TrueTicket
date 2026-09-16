from fastapi import FastAPI

from app.db import init_db
from app.routers import crawl, health, listings, sellers
from app.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title="TrueTicket resale-monitor-service",
    description="재판매 플랫폼 크롤링 · 가격 이상탐지 — 상습 판매 스코어링",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(listings.router)
app.include_router(sellers.router)
app.include_router(crawl.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()
