from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import BehaviorLog, get_db
from app.schemas import BehaviorLogEvent

router = APIRouter(prefix="/api/bot-detection", tags=["behavior"], dependencies=[Depends(require_user)])


@router.post("/behavior-logs", status_code=201)
def collect_behavior_log(event: BehaviorLogEvent, db: Session = Depends(get_db)) -> dict:
    """FR-003: 예매 화면 행동 로그 수집."""
    log = BehaviorLog(
        reservation_session_id=event.reservation_session_id,
        event_type=event.event_type,
        metadata_json=event.metadata,
    )
    db.add(log)
    db.commit()
    return {"logId": log.log_id}
