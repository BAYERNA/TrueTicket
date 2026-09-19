"""
MVP 3주차 스캐폴딩: 정식 얼굴 임베딩 비교 모델(ArcFace 등)은 아직 연동하지 않았다.
현재는 YOLOv8이 검출한 두 얼굴 크롭의 그레이스케일 히스토그램 상관계수로 유사도를
근사하는 자리표시자이며, 인터페이스(compute_similarity)만 유지한 채 추후 실제
임베딩 기반 매칭으로 교체한다.
"""
import cv2
import numpy as np


def compute_similarity(face_crop_a: np.ndarray, face_crop_b: np.ndarray) -> float:
    gray_a = cv2.cvtColor(cv2.resize(face_crop_a, (128, 128)), cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(cv2.resize(face_crop_b, (128, 128)), cv2.COLOR_BGR2GRAY)

    hist_a = cv2.calcHist([gray_a], [0], None, [256], [0, 256])
    hist_b = cv2.calcHist([gray_b], [0], None, [256], [0, 256])
    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)

    correlation = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return float(max(0.0, min(correlation, 1.0)))
