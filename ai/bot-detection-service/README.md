# bot-detection-service

예매 단계 봇·매크로 취득 부정성 스코어링 (FastAPI).

## 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8081
```

## 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/api/bot-detection/behavior-logs` | FR-003 행동 로그 수집 |
| POST | `/api/bot-detection/score` | FR-004 취득 부정성 스코어 조회 (ticket-service가 OpenFeign으로 동기 호출) + Kafka `acquisition-fraud-scores` 발행 |

스코어링 로직은 현재 규칙 기반(`app/scoring.py`)이며, MVP 2주차 이후 scikit-learn 모델로 교체한다.
