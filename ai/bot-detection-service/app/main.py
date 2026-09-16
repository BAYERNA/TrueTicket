from fastapi import FastAPI

from app.db import init_db
from app.routers import behavior, health, score

app = FastAPI(
    title="TrueTicket bot-detection-service",
    description="예매 단계 행동 기반 이상탐지 — 취득 부정성 스코어링",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(behavior.router)
app.include_router(score.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
