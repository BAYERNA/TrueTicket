from fastapi import FastAPI

from app.db import init_db
from app.routers import health, verify

app = FastAPI(
    title="TrueTicket verification-service",
    description="현장 검표 · YOLOv8 얼굴 본인인증",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(verify.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
