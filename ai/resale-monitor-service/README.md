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
| GET | `/api/resale-monitor/listings/{listing_id}` | SCR-08 게시물 단건 조회 |
| GET | `/api/resale-monitor/sellers/{seller_id}` | SCR-09 판매자 프로파일 |
| POST | `/api/resale-monitor/crawl/run` | 정기 스케줄을 기다리지 않고 즉시 1회 크롤 실행 |

## 크롤러 (MVP)

`app/crawler.py`가 `CRAWL_SOURCE_URL`의 페이지를 주기적으로(`CRAWL_INTERVAL_MINUTES`,
기본 15분) 가져와 `.listing` 카드를 파싱하고, ticket-service의 이벤트 카탈로그와
제목을 매칭해 정가를 채운 뒤 `/listings`와 같은 적재 경로(`app/listing_service.py`)로
넣는다. `CRAWL_SOURCE_URL`을 비워두면 스케줄러가 비활성화되고, 수동 트리거
(`POST /crawl/run`)만 남는다.

실제 대상 플랫폼(중고나라·번개장터·티켓베이 등)은 각각 HTML 구조가 달라 플랫폼별
파서가 필요하다 — MVP는 다음 최소 HTML 계약을 따르는 소스 하나만 지원한다:

```html
<div class="listing" data-seller-id="seller-123">
  <span class="title">LG 트윈스 vs 두산 베어스</span>
  <span class="price">150000</span>
</div>
```
