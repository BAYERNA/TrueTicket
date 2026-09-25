from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from apscheduler.schedulers.background import BackgroundScheduler

from app.migrations import run_migrations
from app.routers import behavior, health, score
from app.outbox import dispatch_outbox
from app.db import engine
from app.telemetry import setup_telemetry

_scheduler = BackgroundScheduler()

app = FastAPI(
    title="TrueTicket bot-detection-service",
    description="예매 단계 행동 기반 이상탐지 — 취득 부정성 스코어링",
    version="0.1.0",
)
setup_telemetry(app, engine, "bot-detection-service")

app.include_router(health.router)
app.include_router(behavior.router)
app.include_router(score.router)

# GET /metrics: Prometheus가 스크레이프하는 HTTP 요청 수·지연시간 기본 지표.
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def on_startup() -> None:
    run_migrations()
    _scheduler.add_job(dispatch_outbox, "interval", seconds=5, id="outbox-dispatch")
    _scheduler.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
