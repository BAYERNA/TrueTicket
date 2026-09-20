import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.crawler import run_crawl_once
from app.db import SessionLocal
from app.outbox import dispatch_outbox

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
    _scheduler.add_job(dispatch_outbox, "interval", seconds=5, id="outbox-dispatch")
    if settings.crawl_source_url:
        _scheduler.add_job(
            _crawl_job,
            "interval",
            minutes=settings.crawl_interval_minutes,
            id="resale-crawl",
        )
    else:
        logger.info("CRAWL_SOURCE_URL이 없어 크롤 스케줄만 비활성화합니다.")
    _scheduler.start()
    logger.info("재판매 크롤 스케줄러 시작 (주기: %d분)", settings.crawl_interval_minutes)


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
