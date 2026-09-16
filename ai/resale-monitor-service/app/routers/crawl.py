from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crawler import run_crawl_once
from app.db import get_db

router = APIRouter(prefix="/api/resale-monitor", tags=["crawl"])


@router.post("/crawl/run")
def trigger_crawl(db: Session = Depends(get_db)) -> dict:
    """운영자가 정기 스케줄을 기다리지 않고 즉시 1회 크롤을 실행한다."""
    return run_crawl_once(db)
