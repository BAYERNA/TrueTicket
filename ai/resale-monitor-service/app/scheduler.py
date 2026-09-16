import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.crawler import run_crawl_once
from app.db import SessionLocal

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()


def _crawl_job() -> None:
    db = SessionLocal()
    try:
        result = run_crawl_once(db)
        logger.info("정기 크롤 실행 결과: %s", result)
    finally:
        db.close()


def start_scheduler() -> None:
    if not settings.crawl_source_url:
        logger.info("CRAWL_SOURCE_URL이 설정되지 않아 정기 크롤 스케줄러를 시작하지 않습니다.")
        return

    _scheduler.add_job(
        _crawl_job,
        "interval",
        minutes=settings.crawl_interval_minutes,
        id="resale-crawl",
    )
    _scheduler.start()
    logger.info("재판매 크롤 스케줄러 시작 (주기: %d분)", settings.crawl_interval_minutes)


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
