from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.migrations import run_migrations
from app.routers import behavior, health, score

app = FastAPI(
    title="TrueTicket bot-detection-service",
    description="예매 단계 행동 기반 이상탐지 — 취득 부정성 스코어링",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(behavior.router)
app.include_router(score.router)

# GET /metrics: Prometheus가 스크레이프하는 HTTP 요청 수·지연시간 기본 지표.
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def on_startup() -> None:
    run_migrations()
