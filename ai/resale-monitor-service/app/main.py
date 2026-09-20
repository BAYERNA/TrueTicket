from fastapi import Depends, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.migrations import run_migrations
from app.auth import require_admin
from app.routers import crawl, health, listings, sellers
from app.scheduler import start_scheduler, stop_scheduler
from app.db import engine
from app.telemetry import setup_telemetry

app = FastAPI(
    title="TrueTicket resale-monitor-service",
    description="재판매 플랫폼 크롤링 · 가격 이상탐지 — 상습 판매 스코어링",
    version="0.1.0",
)
setup_telemetry(app, engine, "resale-monitor-service")

app.include_router(health.router)
app.include_router(listings.router, dependencies=[Depends(require_admin)])
app.include_router(sellers.router, dependencies=[Depends(require_admin)])
app.include_router(crawl.router, dependencies=[Depends(require_admin)])

# GET /metrics: Prometheus가 스크레이프하는 HTTP 요청 수·지연시간 기본 지표.
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def on_startup() -> None:
    run_migrations()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()
