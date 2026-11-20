# TrueTicket 암표 대응 에이전트

2026년 11월 17일 구현 결과 · ChatGPT → Claude

기획서 4~11절과 11월 17일 사용자 정정사항을 기준으로 사전 개발물 확인, 저장소 구조 제안, 가상 데이터 생성 작업을 완료했다. 제출 마감은 2026년 11월 23일(월) 17:00 KST다.

## 1. 구현 현황

| 기획서 5절 기능 | 상태 | 오늘 결과 |
| --- | --- | --- |
| P0 ① 외부 암표 게시글 분석 | 부분 | 가상 채널 2개의 텍스트 게시글 80건과 추출 정답, 가상 개인정보 마스킹 사례 10건, 인젝션 비교 사례 5건을 생성했다. HTTP 수집·마스킹·LLM 추출 연동은 미완이다. |
| P0 ② 예매 매칭과 위험 판단 | 부분 | 예매 1,000건, 좌석별 매칭 정답, 판매자 5명에 대한 군집 정답과 위험 등급·규칙 정답을 만들었다. 원본 봇점수 함수에 예매 1,000건의 이벤트를 적용했다. SQL 매칭·군집·규칙 엔진은 미완이다. |
| P0 ③ 승인형 조치 | 부분 | 공연별 25명, 총 50명의 가상 대기열과 재배분에 쓸 기준 사례를 준비했다. 승인·소명·취소·재배분·문서 생성 흐름은 미완이다. |
| P1 운영자 자연어 질의 | 미완 | 구현 전이다. |
| P1 처리 현황 요약 | 미완 | 요약 화면은 구현 전이다. 분석·케이스·실행 로그 시드는 빈 목록이다. |

| 산출물 | 용도 |
| --- | --- |
| `scripts/generate_seed.py` | 시드와 평가셋을 함께 생성하는 표준 라이브러리 기반 CLI |
| `data/seed.json` | SQLite 초기화 입력. 공연 2개, 계정 300개, 예매 1,000건, 게시글 80건, 대기열 50명 |
| `data/evaluation/evaluation_set.json` | `post_id`별 정답과 봇 점수·가상 개인정보·인젝션 테스트 데이터. 에이전트와 가상 마켓 응답에서 분리 |

압축을 푼 저장소 루트에서 다음 명령을 실행하면 두 JSON을 다시 생성한다. 기본 난수 시드는 `20261117`이다. `--output-dir`로 출력 위치를, `--seed`로 좌석 예매 행동과 게시글 순서를 재현할 시드를 지정한다.

```bash
python3 scripts/generate_seed.py
```

### 저장소 구조 제안

| 경로 | 책임 | 상태 |
| --- | --- | --- |
| `legacy/ai/` | 첫 커밋의 원본 세 파일과 출처 기준점 | 5절에 대상 확정 |
| `backend/app/main.py`, `backend/app/api/` | FastAPI 진입점과 기획서 7절 API, 가상 마켓 수집용 HTML 응답 | 제안 |
| `backend/app/db.py`, `backend/app/services/` | SQLite 테이블·시드, 케이스 상태와 승인된 조치 트랜잭션 | 제안 |
| `backend/app/adapters/` | 원본 봇 점수 함수와 가상 마켓 HTTP 수집·파싱의 실행용 어댑터 | 제안 |
| `backend/app/agent/` | 감시 그래프, 사람 승인 단계가 있는 조치 그래프, Pydantic 검증 도구 | 제안 |
| `backend/app/evaluation/` | 정답 파일을 읽고 `/api/eval`용 지표를 계산하는 서버 코드 | 제안 |
| `frontend/src/pages/`, `frontend/src/components/` | React 운영자 대시보드, 의심 큐, 케이스 상세, 가상 리셀 마켓 | 제안 |
| `scripts/`, `data/`, `docs/` | 생성기, 데모 시드 및 평가셋, Claude 전달 보고서 | 이번 작업분 생성 |

프론트의 `/market`은 React 화면으로 두고, 가상 마켓 HTML 피드는 FastAPI에서 렌더링하는 구조를 제안한다. HTTP 클라이언트는 렌더링된 게시글을 받아야 한다. 피드의 지정된 내부 경로에서만 수집하고, 평가셋은 백엔드 평가 경로에서만 읽는다.

## 2. 바뀐 점과 이유

| 항목 | 적용 |
| --- | --- |
| 리셀 수집 | ZIP의 HTTP GET과 BeautifulSoup 선택자가 재사용 대상이다. 원본의 `.listing` 구조를 살리면서 게시글 ID·본문·채널을 보존하고 가격 미상의 글도 수집하도록 확장할 계획이다. |
| 봇 점수 | `compute_rule_based_score`의 기존 가중치와 계산을 사용한다. 원본 API 플래그 설정은 0.7이며, 새 R4 판단에는 기획서의 0.8을 적용한다. 평가 기준은 매칭된 예매별 점수다. |
| 위험 판단 | 기존 리셀 점수 3종은 참고용이다. `assess_risk`는 기획서 7절의 R1~R5로 신규 구현할 계획이다. 정답의 판매가는 장당 원화 정수이며, 예매의 `price_paid`는 등급 정가와 장당 예매 수수료의 합이다. |
| OCR 및 인프라 | 게시글은 텍스트만 담았다. OCR과 이미지 필드는 범위에서 제외했다. 실행 앱은 FastAPI와 SQLite를 사용할 계획이다. |
| 시드와 정답 | 실행 시드에는 공개 게시글만 저장했다. 라벨·정답 좌석·매칭 ID·위험 등급·판매자 군집은 동일한 `post_id`의 평가 파일에 둬 정답 노출을 피한다. |

두 공연은 각각 1회차로 구성했다. 좌석의 예매 식별 기준은 공연 ID, 회차 ID, 좌석이다. 기획서의 `matched_booking_id`를 구현할 때 다수 좌석을 확인할 수 있도록 정답 파일에 `matched_booking_ids` 배열을 뒀다. 대기열은 공연·등급별로 `joined_at` 순서, 동률이면 `fan_id` 순서를 사용한다.

## 3. 배포 정보

프론트 URL, 백엔드 URL, 로그인 없는 데모 진입 경로, 서버 플랜, API 사용량 한도는 미설정이다. 현재 실행 진입점은 로컬 데이터 생성 CLI다.

## 4. 기술 스택과 버전

| 범위 | 사용 또는 예정 |
| --- | --- |
| 데이터 생성·검증 | Python 3.12.14에서 실행했다. 3.11 문법 검사를 통과했다. 생성기는 `argparse`, `json`, `random`, `collections`, `dataclasses`, `datetime`, `pathlib` 표준 라이브러리로 동작한다. |
| 봇 점수 원본 | `bot-rules-v1`로 표시된 규칙 스코어. 직접 의존성은 Python `statistics`다. |
| 리셀 모듈 원본 의존성 | 첨부 ZIP의 `requirements.txt` 기준 `httpx==0.27.2`, `beautifulsoup4==4.12.3`. 어댑터의 설치 버전은 통합 시 확정한다. |
| 실행 앱 목표 | Python 3.11, FastAPI, LangGraph, Pydantic, SQLite, React, Vite, TypeScript |
| LLM·임베딩 | 모델명과 버전 미선정. 오늘 데이터 생성 및 봇점수 검증에 런타임 모델 호출은 없었다. |

## 5. 사전 개발물 재사용 목록

경로는 ZIP의 `TrueTicket_existing_modules/ai/` 아래를 기준으로 기재했다.

| 원본 파일·함수 | 입력 → 출력 | 의존성과 처리 |
| --- | --- | --- |
| `bot-detection-service/app/scoring.py` · `compute_rule_based_score(behavior_events)` | `list[dict]`의 `click.metadata.interval_ms`와 `automation_signature` → 소수점 넷째 자리까지의 0~1 점수. 빈 입력은 0.0 | Python `statistics`. 3개 이상의 클릭으로 간격 변동계수를 계산한다. 균일도 가중치 0.6, 자동화 흔적 가중치 0.4. 원본 그대로 검증했고 `bot_score`에서 재사용한다. 근거 표시는 어댑터에서 클릭 간격과 흔적 건수를 붙인다. |
| `resale-monitor-service/app/crawler_client.py` · `fetch_html(url)` | URL 문자열 → 응답 HTML 문자열. `httpx.HTTPError` 시 `None` | `httpx`, Python `logging`. 원본은 10초 타임아웃과 리디렉션 추적을 사용한다. 어댑터는 가상 피드 URL로 고정하고 리디렉션을 끈 HTTP 요청과 오류 처리로 옮긴다. |
| `resale-monitor-service/app/crawler.py` · `parse_listings(html)` | HTML 문자열 → `list[dict]`의 `title: str`, `price: float`, `seller_id: str` | 함수 안에서는 BeautifulSoup과 로거를 쓴다. `.listing`, `.title`, `.price`, `data-seller-id`를 읽고 쉼표를 지운 숫자를 파싱한다. 파일 전체를 import하면 SQLAlchemy 및 기존 `app` 서비스들이 필요하다. 수집 어댑터에는 함수의 HTML 파싱 부분을 옮긴다. |

원본 파서는 제목·가격·판매자 ID가 없거나 가격이 숫자로 변환되지 않으면 행을 건너뛴다. 새 수집 어댑터는 `data-post-id`와 본문을 읽고, 가격 필드를 선택값으로 보존해야 한다. 가격이나 좌석이 빠진 글은 평가셋의 ‘확인 불가’ 경로를 검증하는 입력이다. HTTP 조회 실패와 게시글 0건은 다른 결과로 처리할 계획이다.

| 참조만 한 파일 | 경계 |
| --- | --- |
| `bot-detection-service/app/routers/score.py`, `app/config.py` | 라우터가 DB 행동 로그를 `event_type`과 `metadata` 딕셔너리로 만들어 함수에 전달하는 것을 확인했다. 기존 라우터와 설정은 기준 커밋 대상이 아니다. |
| `resale-monitor-service/app/scoring.py` | `compute_price_anomaly_score`, `compute_seller_repetition_score`, `compute_habitual_score`는 배율·반복 게시 참고용이다. |
| `resale-monitor-service/app/crawler.py`의 `run_crawl_once`, `app/listing_service.py`, `app/ticket_client.py` | 원본은 별도 서비스에서 공연 카탈로그를 조회하고 SQLAlchemy·outbox로 적재한다. 이 실행 경로는 이번 앱의 의존성 범위 밖이다. |

### 첫 커밋 `pre-hackathon` 대상

아래 세 파일을 첨부 ZIP 그대로 복사하는 구성을 제안한다. 리셀 원문 `crawler.py`는 사전 개발물 비교용이며, 실행 코드는 `backend/app/adapters/`에서 신규 커밋으로 작성한다.

| ZIP 내부 경로 | 새 저장소 경로 | 원본 SHA-256 |
| --- | --- | --- |
| `TrueTicket_existing_modules/ai/bot-detection-service/app/scoring.py` | `legacy/ai/bot-detection-service/app/scoring.py` | `b02acb5c01c54c7b7bdc20f499d42351979e7f681d588572f853b320622abe7a` |
| `TrueTicket_existing_modules/ai/resale-monitor-service/app/crawler_client.py` | `legacy/ai/resale-monitor-service/app/crawler_client.py` | `82ed29d83b07a6e0187f735b71a5c379d85beaf69fc4df953846b4c4067cab06` |
| `TrueTicket_existing_modules/ai/resale-monitor-service/app/crawler.py` | `legacy/ai/resale-monitor-service/app/crawler.py` | `03b567d0490ccadd64a5fbe2d67bfdb6e2605cbe8bf4bd0e0077033ccdda9c4e` |

첫 커밋 메시지 제안은 `사전 개발물 가져오기(해커톤 이전 개발)`이다. 커밋과 태그는 제안 상태다. 생성기·시드·평가셋·이 문서와 후속 어댑터는 해커톤 작업 커밋에 속한다.

## 6. 평가 결과

| 정답 라벨 | 건수 | 기획서 7절 예상 위험 등급 |
| --- | ---: | --- |
| 정가 양도 | 20 | 낮음 |
| 웃돈 1장(2배 미만) | 15 | 중간 |
| 부정판매 기준 충족 | 25 | 높음 |
| 사기 의심 | 10 | 중간 |
| 판단 불가 | 10 | 확인 불가 |
| 합계 | 80 | |

시드와 정답 파일의 게시글 ID를 대조했고, 예매 1,000건의 공연·계정 참조 및 회차별 좌석 고유성을 검증했다. 판매자 5명은 각 5건을 가상 채널 두 곳에 게시하며 판매자당 별칭 3개를 쓴다. 인젝션 5건에는 같은 글의 인젝션 이전 본문이 있고, 마스킹 10건에는 가상 이름·전화·계좌·이메일에 대한 검증값이 있다. 기본 시드 재생성 시 두 파일의 바이트가 일치했고, 다른 난수 시드에서도 레코드 수가 유지됐다.

| 기존 봇 함수 검증 사례 | 실측 점수 | R4 임계값 0.8 |
| --- | ---: | --- |
| 균일 클릭, 흔적 1회 | 0.720 | 미달 |
| 임계값 직전 | 0.798 | 미달 |
| 임계값과 동일 | 0.800 | 충족 |
| 균일 클릭, 흔적 2회 | 0.840 | 충족 |
| 균일 클릭, 흔적 3회 | 0.960 | 충족 |

원본 봇 코드로 예매 이벤트 1,000건을 실제 계산했다. 점수 정답을 부여한 예매는 6건이며, 해당 예매 6건 모두 일치했다. R4에 해당하는 예매는 전체 4건이다. R4가 붙은 게시글 3건 중 한 건에는 예매 2건이 매칭된다. 가격 경계 사례는 구입가와 동일한 10건, 구입가보다 1원 비싼 3건, 정가의 정확히 2배인 5건이다.

기획서 8절의 추출 정확도, 부정판매 탐지율, 정상 양도 오탐률, 판매자 군집 정확도, 마스킹 누락, 인젝션 방어율, 건당 처리 시간과 비용은 모두 미측정이다. 분석 실행 전이라 실제 오답 3건과 원인도 기록할 수 없다. 위 표의 라벨 수와 등급은 평가셋의 정답이며, 봇 점수는 기존 함수의 실측값이다.

## 7. 화면 캡처 목록

11월 17일 캡처는 없다. 기본 시드에는 한빛 겨울 콘서트의 `post-017`에 예매 `booking-0001`·`booking-0002`가 대응한다. 첫 번째 R석 대기자는 `fan-001`이다. 감시 → 케이스 근거 확인 → 운영자 승인 → 소명·취소·재배분 → 신고서 초안 흐름을 검증할 때 쓸 수 있다. 화면 캡처에는 이 가상 시드만 사용한다.

## 8. 알려진 오류와 한계

- 로컬 실행 환경에 Python 3.11 인터프리터가 없어 3.12.14에서 실행했다. 3.11 문법 검사는 통과했다.
- 실제 플랫폼 및 실제 이용자의 분포가 반영되지 않은 가상 데이터다. 정답 성능은 에이전트 통합 후 측정한다.
- 가상 공연당 1회차다. 동일 공연의 다회차 모호성은 현재 평가셋에 포함되지 않았다.
- 현재 산출물은 JSON 시드와 평가셋이다. SQLite 적재와 웹앱에서의 분석·조치·배포는 후속 작업이다.

## 9. AI 사용 기록

| 주체 | 수행한 일 |
| --- | --- |
| Claude | TrueTicket 프로토타입 기획서와 7절 평가셋 구성, 12절 보고 양식을 작성했다. |
| 송형규 | 작업 범위와 마감을 지정하고, 재사용 방식·실제 라이브러리·OCR 제외·단일 백엔드 결정을 명시했다. 기획서와 기존 코드 ZIP을 제공했다. |
| ChatGPT | 원본 함수·의존성을 점검하고 보존할 파일의 해시를 계산했다. 저장소 구조를 제안하고 생성기·가상 데이터·평가셋·보고서를 작성했다. 생성 재현, 입력 및 참조 정합성, 원본 봇 함수의 경계값을 검증했다. |

## 10. 외부 자원 목록

| 이름 | 출처·이용 조건 | 사용 위치 |
| --- | --- | --- |
| Python 표준 라이브러리 | Python Software Foundation License. [Python 라이선스](https://docs.python.org/3/license.html) | 생성기와 검증, 기존 봇 점수 함수 |
| 기존 TrueTicket 모듈 | 사용자 제공 `TrueTicket_existing_modules.zip`. ZIP에서 원본 저장소 주소, 파일별 작성자, 라이선스와 실제 개발 시기를 확인할 수 없었다. | 원본 조사, 봇 함수 검증, 첫 커밋 대상 3개 |
| 가상 시드 및 평가셋 | 이 작업에서 생성. 기획서 7절의 데이터 구성과 8절의 평가 입력을 반영했다. | `data/seed.json`, `data/evaluation/evaluation_set.json` |

사전 개발 내역에 기록할 **두 모듈의 실제 개발 연·월, 원본 저장소 주소, 작성자 또는 팀원별 기여 범위, 재사용 이용 조건**을 형규님에게 확인해야 한다. 외부 데이터·이미지·폰트 사용은 없다.
