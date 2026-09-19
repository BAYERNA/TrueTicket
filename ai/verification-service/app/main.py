from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.db import init_db
from app.routers import health, verify

app = FastAPI(
    title="TrueTicket verification-service",
    description="현장 검표 · YOLOv8 얼굴 본인인증",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(verify.router)

# GET /metrics: Prometheus가 스크레이프하는 HTTP 요청 수·지연시간 기본 지표.
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
