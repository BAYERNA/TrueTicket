from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_admin, require_internal
from app.config import settings
from app.db import BehaviorLog, BotScore, OutboxEvent, get_db
from app.schemas import BehaviorScoreRequest, BehaviorScoreResponse, BotScoreLogEntry, ScoreFeedbackRequest
from app.scoring import compute_rule_based_score
from app.model_metrics import feedback_counter, flagged_counter, score_histogram

router = APIRouter(prefix="/api/bot-detection", tags=["score"])


@router.post("/score", response_model=BehaviorScoreResponse, dependencies=[Depends(require_internal)])
def score_session(request: BehaviorScoreRequest, db: Session = Depends(get_db)) -> BehaviorScoreResponse:
    """
    FR-004: ticket-service가 좌석 선점 직전에 동기 호출(OpenFeign)하는 즉시 응답 스코어링.
    동시에 같은 스코어를 Kafka로도 발행해(Choreography), notification-service의 AND 엔진이
    나중에 도착하는 상습 판매 스코어와 조인할 수 있도록 한다.
    """
    logs = db.scalars(
        select(BehaviorLog).where(BehaviorLog.reservation_session_id == request.reservation_session_id)
    ).all()
    events = [{"event_type": log.event_type, "metadata": log.metadata_json} for log in logs]

    score = compute_rule_based_score(events)
    is_flagged = score >= settings.acquisition_fraud_threshold

    evaluated_at = datetime.now(timezone.utc)
    db.add(
        BotScore(
            reservation_session_id=request.reservation_session_id,
            acquisition_fraud_score=score,
            is_flagged=is_flagged,
            evaluated_at=evaluated_at,
            model_version=settings.model_version,
        )
    )
    db.add(OutboxEvent(topic="acquisition-fraud-scores", payload={
        "reservationSessionId": request.reservation_session_id,
        "acquisitionFraudScore": score,
        "isFlagged": is_flagged,
        "evaluatedAt": evaluated_at.isoformat(),
    }))
    db.commit()
    score_histogram.observe(score)
    if is_flagged:
        flagged_counter.labels(settings.model_version).inc()

    return BehaviorScoreResponse(acquisition_fraud_score=score, is_flagged=is_flagged)


@router.get("/scores", response_model=list[BotScoreLogEntry], dependencies=[Depends(require_admin)])
def list_scores(db: Session = Depends(get_db)) -> list[BotScoreLogEntry]:
    """SCR-10: 예매 세션별 매크로/봇 탐지 스코어와 근거를 확인한다."""
    scores = db.scalars(select(BotScore).order_by(BotScore.evaluated_at.desc()).limit(200)).all()
    return [
        BotScoreLogEntry(
            score_id=s.score_id,
            reservation_session_id=s.reservation_session_id,
            acquisition_fraud_score=s.acquisition_fraud_score,
            is_flagged=s.is_flagged,
            evaluated_at=s.evaluated_at,
            model_version=s.model_version,
            review_label=s.review_label,
        )
        for s in scores
    ]


@router.post("/scores/{score_id}/feedback", dependencies=[Depends(require_admin)])
def record_feedback(score_id: str, request: ScoreFeedbackRequest, db: Session = Depends(get_db)) -> dict:
    score = db.get(BotScore, score_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    score.review_label = request.label
    score.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    feedback_counter.labels(score.model_version, request.label).inc()
    return {"scoreId": score_id, "reviewLabel": request.label}
