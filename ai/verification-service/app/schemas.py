from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """JSON 경계는 camelCase로 통일한다 (Flutter 앱과의 계약 일치)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class VerificationResponse(CamelModel):
    verification_id: str
    reservation_id: str
    face_match_result: bool
    face_match_score: float
    duplicate_scan_flag: bool
    snapshot_uri: str
