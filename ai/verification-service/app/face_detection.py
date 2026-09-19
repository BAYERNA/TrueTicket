"""
FR-011: YOLOv8 얼굴 검출. 사전 학습된 얼굴 검출 가중치(예: yolov8n-face.pt)를
별도로 내려받아 YOLO_FACE_MODEL_PATH에 배치해야 동작한다. 가중치가 없는 개발 환경에서도
서비스 자체는 기동되도록 모델 로드 실패를 흡수하고 None을 반환한다.
"""
from __future__ import annotations

import logging

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_load_attempted = False


def _get_model():
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model

    _model_load_attempted = True
    try:
        from ultralytics import YOLO

        _model = YOLO(settings.yolo_face_model_path)
    except Exception:
        logger.warning(
            "YOLOv8 얼굴 검출 모델을 불러오지 못했습니다 (%s). 가중치 파일이 있는지 확인하세요.",
            settings.yolo_face_model_path,
        )
        _model = None

    return _model


def detect_face_crop(image: np.ndarray) -> np.ndarray | None:
    """이미지에서 신뢰도가 가장 높은 얼굴 영역을 잘라 반환한다. 검출 실패 시 None."""
    model = _get_model()
    if model is None:
        return None

    results = model.predict(source=image, verbose=False)
    if not results or len(results[0].boxes) == 0:
        return None

    boxes = results[0].boxes
    best_idx = int(boxes.conf.argmax())
    x1, y1, x2, y2 = [int(v) for v in boxes.xyxy[best_idx].tolist()]
    return image[max(y1, 0):y2, max(x1, 0):x2]
