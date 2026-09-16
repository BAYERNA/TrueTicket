# verification-service

현장 검표 · YOLOv8 얼굴 본인인증 (FastAPI).

## 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8083
```

얼굴 검출을 실제로 동작시키려면 YOLOv8 얼굴 검출 가중치(예: `yolov8n-face.pt`)를
받아 `YOLO_FACE_MODEL_PATH` 경로에 두어야 한다. 가중치가 없어도 서비스는 기동되며,
이 경우 얼굴 크롭 없이 원본 프레임으로 유사도 비교를 대체한다(개발 편의용 폴백).

## 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/api/verification/verify` | FR-010/011/011-1: QR 조회(ticket-service) → 중복 사용 확인 → 얼굴 검출·대조 → MinIO 스냅샷 저장 → verification_logs 기록 |

`face_matching.py`의 히스토그램 기반 유사도는 MVP 3주차 자리표시자이며, 이후 ArcFace 등
실제 얼굴 임베딩 모델로 교체한다.
