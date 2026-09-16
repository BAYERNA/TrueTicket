from datetime import datetime

from pydantic import BaseModel, Field


class BehaviorLogEvent(BaseModel):
    reservation_session_id: str
    event_type: str = Field(description="mouse_move | click | keypress | page_load 등")
    metadata: dict = Field(default_factory=dict)


class BehaviorScoreRequest(BaseModel):
    reservation_session_id: str
    event_type: str = "SCORE_REQUEST"


class BehaviorScoreResponse(BaseModel):
    acquisition_fraud_score: float
    is_flagged: bool


class BotScoreLogEntry(BaseModel):
    reservation_session_id: str
    acquisition_fraud_score: float
    is_flagged: bool
    evaluated_at: datetime
