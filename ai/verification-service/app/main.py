from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_fastapi_instrumentator import Instrumentator

from app.migrations import run_migrations
from app.routers import health, verify
from app.db import engine
from app.telemetry import setup_telemetry
from app.retention import purge_expired_snapshots

_scheduler = BackgroundScheduler()

app = FastAPI(
    title="TrueTicket verification-service",
    description="현장 검표 · YOLOv8 얼굴 본인인증",
    version="0.1.0",
)
setup_telemetry(app, engine, "verification-service")

app.include_router(health.router)
app.include_router(verify.router)

# GET /metrics: Prometheus가 스크레이프하는 HTTP 요청 수·지연시간 기본 지표.
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def on_startup() -> None:
    run_migrations()
    _scheduler.add_job(purge_expired_snapshots, "interval", hours=1, id="snapshot-retention")
    _scheduler.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
