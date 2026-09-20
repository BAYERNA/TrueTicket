import uuid
from datetime import datetime, timezone
from typing import Annotated

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import VerificationLog, get_db
from app.face_detection import detect_face_crop
from app.face_matching import compute_similarity
from app.minio_client import upload_snapshot
from app.schemas import VerificationResponse
from app.ticket_client import get_reservation_by_qr
from app.auth import require_staff

router = APIRouter(prefix="/api/verification", tags=["verify"])


def _decode_image(data: bytes) -> np.ndarray:
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image payload")
    return image


@router.post("/verify", response_model=VerificationResponse)
async def verify(
    claims: Annotated[dict, Depends(require_staff)],
    qr_code: str = Form(...),
    live_image: UploadFile = File(...),
    reference_image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> VerificationResponse:
    """
    FR-010/FR-011: QR 스캔 → 중복 사용 확인 → YOLOv8 얼굴 검출 → 신분증(reference_image)
    대조 순서로 처리한다. live_image는 현장 웹캠 캡처, reference_image는 예매 시 등록된
    본인 확인용 이미지(신분증 등)를 가정한다.
    """
    reservation = get_reservation_by_qr(qr_code)
    if reservation is None:
        raise HTTPException(status_code=404, detail="유효하지 않은 QR 코드입니다")

    reservation_id = reservation["reservationId"]

    already_verified = db.scalar(
        select(VerificationLog).where(
            VerificationLog.reservation_id == reservation_id,
            VerificationLog.face_match_result.is_(True),
        )
    )
    if already_verified is not None:
        raise HTTPException(status_code=409, detail="이미 입장 처리된 QR 코드입니다 (중복 사용 의심)")

    live_bytes = await live_image.read()
    reference_bytes = await reference_image.read()
    live_array = _decode_image(live_bytes)
    reference_array = _decode_image(reference_bytes)

    live_face = detect_face_crop(live_array)
    reference_face = detect_face_crop(reference_array)
    # 얼굴 검출 모델(가중치)이 없는 개발 환경에서도 서비스가 동작하도록, 검출 실패 시
    # 원본 프레임 전체로 유사도 비교를 대체한다.
    similarity = compute_similarity(live_face if live_face is not None else live_array,
                                     reference_face if reference_face is not None else reference_array)
    face_match_result = similarity >= settings.face_match_threshold

    object_name = f"{reservation_id}/{uuid.uuid4()}.jpg"
    snapshot_uri = upload_snapshot(object_name, live_bytes)

    log = VerificationLog(
        reservation_id=reservation_id,
        qr_scanned_at=datetime.now(timezone.utc),
        face_match_result=face_match_result,
        face_match_score=similarity,
        snapshot_uri=snapshot_uri,
        duplicate_scan_flag=False,
        verified_by=claims["sub"],
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        # 위 already_verified 조회와 이 commit 사이에 같은 예매 건이 다른 게이트에서
        # 거의 동시에 스캔·통과된 경합 상황. DB의 partial unique 제약이 막아준 것이므로
        # 먼저 커밋된 쪽만 인정하고 이쪽은 중복으로 응답한다.
        db.rollback()
        raise HTTPException(status_code=409, detail="이미 입장 처리된 QR 코드입니다 (중복 사용 의심)")
    db.refresh(log)

    return VerificationResponse(
        verification_id=log.verification_id,
        reservation_id=log.reservation_id,
        face_match_result=log.face_match_result,
        face_match_score=log.face_match_score,
        duplicate_scan_flag=log.duplicate_scan_flag,
        snapshot_uri=log.snapshot_uri,
    )
