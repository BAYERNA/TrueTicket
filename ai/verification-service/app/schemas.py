from pydantic import BaseModel


class VerificationResponse(BaseModel):
    verification_id: str
    reservation_id: str
    face_match_result: bool
    face_match_score: float
    duplicate_scan_flag: bool
    snapshot_uri: str
