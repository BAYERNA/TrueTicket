# resale-monitor-service

재판매 플랫폼 크롤링 · 가격 이상탐지 · 상습 판매자 판별 (FastAPI).

## 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8092
```

## 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/api/resale-monitor/listings` | FR-006/007/008/009 게시물 적재 + 스코어링 + Kafka `habitual-resale-scores` 발행 |
| GET | `/api/resale-monitor/listings` | SCR-07 대시보드용 목록 |
| GET | `/api/resale-monitor/sellers/{seller_id}` | SCR-09 판매자 프로파일 |

크롤러(중고거래/리셀 플랫폼 수집기)는 별도 배치/스케줄러로 구현해 이 서비스의
`/listings` 엔드포인트로 수집 결과를 적재하는 구조를 전제로 한다 (MVP 4주차).
