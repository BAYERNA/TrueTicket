from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """
    Kotlin(ticket-service)/TypeScript(frontend)와의 JSON 경계는 camelCase로 통일한다.
    Python 쪽 속성명은 PEP8대로 snake_case를 유지하되, 요청/응답 바디는 alias로 변환한다.
    populate_by_name=True라서 snake_case 입력(curl 테스트 등)도 계속 허용한다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BehaviorLogEvent(CamelModel):
    reservation_session_id: str
    event_type: str = Field(description="mouse_move | click | keypress | page_load 등")
    metadata: dict = Field(default_factory=dict)


class BehaviorScoreRequest(CamelModel):
    reservation_session_id: str
    event_type: str = "SCORE_REQUEST"


class BehaviorScoreResponse(CamelModel):
    acquisition_fraud_score: float
    is_flagged: bool


class BotScoreLogEntry(CamelModel):
    reservation_session_id: str
    acquisition_fraud_score: float
    is_flagged: bool
    evaluated_at: datetime
