# TrueTicket 암표 대응 에이전트

11/18 작업 결과 · ChatGPT → Claude

11/17 결과를 반영한 갱신 기획서의 11-1절을 인수 기준으로 사용했다. T1~T3의 기능 조건을 검증했다. 제출 마감은 2026년 11월 23일(월) 17:00 KST다.

## 1. 구현 현황

### T1. 가상 데이터·평가셋

| 11-1절 조건 | 상태 | 확인 결과 |
| --- | --- | --- |
| 같은 시드로 바이트까지 재현 | 충족 | Python 3.11.18에서 시드 20261117로 다시 생성한 두 JSON의 바이트가 일치했다. |
| 공연 2개, 계정 300개, 예매 1,000건, 게시글 80건, 대기열 50명 | 충족 | 공연당 1회차, 대기열 공연별 25명이다. |
| 게시글마다 정답을 별도 파일에 보관 | 충족 | 80개 게시글 ID가 모두 평가 파일에 있다. 연결된 예매 ID, 위험 등급·규칙, 판매자 군집 등 정답을 보존했다. |
| 판매자 5명 × 5건, 2개 채널, 판매자당 별칭 3개 | 충족 | 동일 판매자의 글에 채널 2개와 별칭 3개가 있다. |
| 원본 봇 점수와 평가셋 일치 | 충족 | 예매 1,000건의 어댑터 점수가 원본과 모두 같았다. 경계 예매 6건이 정답과 일치했고 R4 해당 예매는 4건이다. |
| 마스킹용 가상 정보 10건, 인젝션 비교 5건 | 충족 | 시드와 평가 파일에서 입력 사례 수를 확인했다. |
| 기준 시연의 게시글·예매·대기자 고정 | 충족 | `post-017` ↔ `booking-0001`·`booking-0002`, 첫 R석 대기자는 `fan-001`이다. |
| 확인 필요 ① `post-017` 높음 및 R1과 (R2 또는 R3) | 충족 | 정답은 높음, 규칙은 R1·R2·R4다. 장당 137,000원은 구입가 112,000원을 초과한다. A-01-01, A-01-02 두 좌석으로 R2를 충족한다. |
| 확인 필요 ② 부정판매 판매자 5명의 실제 예매 연결 | 충족 | 25건 모두 시드의 유효한 예매와 연결된다. 공연·회차·좌석으로 대조한 결과, 판매자별 고유 좌석 수는 6·5·5·5·5개다. |
| 확인 필요 ③ 정상 계정의 봇 점수 0.3 이하 | 충족 | 정상 계정 275개의 예매 974건을 계산했다. 최고 0.2866이며 0.3 초과는 0건이다. |
| 확인 필요 ④ 없는 좌석·취소된 예매 각각 3건 이상 | 충족 | 없는 좌석 10건, 취소 예매 0건에서 7건·3건으로 보완했다. 두 경우 모두 정답 매칭은 빈 배열이며 실패 이유를 별도 기록했다. |

### T2. 기존 코드 이식

| 11-1절 조건 | 상태 | 확인 결과 |
| --- | --- | --- |
| 첫 커밋·태그·SHA-256 | 충족 | 루트 커밋 `7237a53`에 10절의 파일 3개만 있다. 해당 커밋에 `pre-hackathon` 태그가 있고 세 Git blob 해시가 모두 기획서와 일치했다. |
| 봇 점수 경계 재현 | 충족 | 0.720·0.798·0.800·0.840·0.960을 원본과 동일하게 재현했다. |
| 클릭 간격 변동계수·자동화 흔적 수 반환 | 충족 | `bot_score`의 근거에 클릭 간격 수, 변동계수, 자동화 흔적 건수가 있다. 0.800 사례는 변동계수 0.0666667, 흔적 2건이다. |
| 원본 HTML 형식과 확장 필드·선택 가격 | 충족 | `.listing`, `.title`, `.price`, `data-seller-id`를 유지했다. 게시글 ID·본문·채널을 읽으며 가격 미등록 56건도 수집했다. |
| HTTP 조회 실패와 정상 0건 구분 | 충족 | 정상 0건은 `ok`와 빈 목록을 반환한다. 연결 실패와 HTTP 오류는 `failed` 및 별도 오류 정보를 반환한다. 실제 200·302·연결 종료로 검증했다. |
| 단일 Uvicorn 명령 실행 | 충족 | 의존성 설치 후 Python 3.11.18에서 `uvicorn backend.app.main:app`로 기동했다. Kafka·PostgreSQL·JWT 의존성 없이 SQLite와 HTTP 수집이 작동했다. |

### T3. SQLite 적재·가상 마켓·HTTP 수집

| 11-1절 조건 | 상태 | 확인 결과 |
| --- | --- | --- |
| SQLite 시드 적재 및 초기화, 평가 파일 분리 | 충족 | 8개 테이블을 만들고 가상 데이터를 적재했다. `POST /api/demo/reset` 뒤 2·300·1,000·80·50건으로 돌아왔으며 분석·케이스·실행 로그는 0건이었다. DB와 공개 응답에는 평가 정답을 적재하지 않았다. |
| FastAPI 피드 80건을 `collect_posts`가 HTTP로 수집 | 충족 | 실제 루프백 HTTP에서 게시글 80건의 ID·제목·본문·채널·가격을 시드와 대조했다. |
| React 마켓 등록 글을 다음 감시에서 수집 | 충족 | Vite 빌드를 DOM 환경에서 실행해 가격 미정 글을 등록했다. 실제 HTTP 감시 결과가 81건이 됐고 새 글 ID가 응답과 화면에 나타났다. 초기화 후 80건을 확인했다. |
| 내부 피드 고정·리디렉션 미추적 | 충족 | `127.0.0.1`의 지정 포트와 `/api/market/feed`를 사용한다. 302 응답에서 이동 경로로 두 번째 요청이 발생하지 않은 것을 확인했다. |

T4 모델은 사용자 선택 대기다. 게시글 마스킹·추출, 케이스에서 예매·위험 근거를 보여 주는 시연, 소명·취소·재배분, 공개 배포는 각각 이후 작업이다.

## 2. 바뀐 점과 이유

- 기존 사기 의심 사례 중 3건을 시드의 취소된 예매 좌석으로 바꿨다. 게시글을 추가로 늘리지 않고도 80건의 정답 분포와 기준 시연 ID를 보존할 수 있다.
- 공개 시드에 선택값 `price`를 넣고, 평가셋에만 `matching_failure_reason`을 넣었다. 수집기가 가격 미등록 글을 보존하며, 후속 매칭기가 없는 좌석과 취소된 예매를 평가할 수 있다.
- 개발 중에는 FastAPI가 빌드된 React 화면과 API를 같이 제공한다. T3의 `/api/agent/runs`는 실제 수집 단계의 결과를 기록한다.

## 3. 배포 정보

| 항목 | 상태 |
| --- | --- |
| 프론트·백엔드 URL | 로컬 프론트 `http://127.0.0.1:8000/market`, 백엔드 `http://127.0.0.1:8000` |
| 데모 진입 | 의존성 설치와 프론트 빌드 후 `uvicorn backend.app.main:app`를 실행하고 `/market`에 접속한다. 작업 ZIP에는 빌드 결과도 들어 있다. |
| 서버 플랜·API 사용량 한도 | 공개 배포 및 한도 설정 전이다. 이번 작업에서 LLM·임베딩 호출은 없었다. |
| Git 이력 | `main`과 `pre-hackathon` 태그의 이력을 ZIP 내부 `TrueTicket.git.bundle`로 제공한다. 현재 작업 이력은 로컬 저장소에 있다. |

## 4. 기술 스택과 버전

Python 3.11.18, SQLite 3.53.1, FastAPI 0.141.1, Starlette 1.10.0, Pydantic 2.13.4, Uvicorn 0.52.1, httpx 0.28.1, Beautiful Soup 4.12.3에서 검증했다. 프론트 빌드는 Node.js 24.22.1, React·React DOM 19.3.1, Vite 8.3.8, TypeScript 5.9.3을 사용했다.

### T4 후보 모델

표준 API 요금은 100만 토큰당 USD다. LLM 예시는 동일한 80건을 한 번씩 처리하고 건당 입력 1,200토큰, 과금 출력 250토큰으로 가정했다. 실제 출력·추론 토큰과 재시도 횟수에 따라 비용이 달라진다.

| LLM ID | 입력 / 출력 | 80건 추정 | 한국어 평가에서 확인할 항목 |
| --- | ---: | ---: | --- |
| `gpt-5.6-luna` | $0.20 / $1.20 | $0.0432 | 저비용 후보. 한국어 좌석·금액·수량 구조화와 `아옮`·`플미`를 같은 JSON 스키마로 검증한다. [모델·요금](https://developers.openai.com/api/docs/models/gpt-5.6-luna) |
| `gpt-5.6-terra` | $2.00 / $12.00 | $0.4320 | 복합 해석 후보. 정가·수고비·두 장 합계가 한 문장에 섞인 경우 장당 금액 해석과, 누락 필드·인젝션 처리를 중점 비교한다. [모델·요금](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |

두 모델은 Structured Outputs를 지원한다. 한국어 암표 게시글의 직접 비교 실측치는 아직 없다. 모델 비교에는 동일한 마스킹 본문·프롬프트·스키마를 쓰고 필드 정확도 90%, 인젝션 5개 기준, `post-017`의 장당 137,000원·좌석 두 개·수량 2를 확인한다. [GPT-5.6 모델군](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6)

| 임베딩 ID | 입력 단가 | 80건 추정 | 기본 차원 / 공개 지표 |
| --- | ---: | ---: | --- |
| `text-embedding-3-small` | $0.02 | $0.00032 | 1,536차원, 종합 MTEB 62.3%. [모델·요금](https://developers.openai.com/api/docs/models/text-embedding-3-small) |
| `text-embedding-3-large` | $0.13 | $0.00208 | 3,072차원, 종합 MTEB 64.6%. OpenAI가 비영어를 포함한 고성능 모델로 설명한다. [모델·요금](https://developers.openai.com/api/docs/models/text-embedding-3-large) |

임베딩 비용은 게시글당 입력 200토큰을 가정했다. MTEB 수치는 공식 가이드의 종합 지표다. 한국어 군집은 별칭이 다른 동일 판매자 쌍과 같은 공연의 서로 다른 판매자 쌍을 대조해 5개 정답 군집 일치율과 오군집을 비교한다. 두 종류 모두 모델 선택과 계정에서의 호출 가능 여부 확인이 남았다. [임베딩 가이드](https://developers.openai.com/api/docs/guides/embeddings)

## 5. 사전 개발물 재사용 목록

사용자 확인 출처는 [BAYERNA/TrueTicket 작업 브랜치](https://github.com/BAYERNA/TrueTicket/tree/claude/trueticket-workspace-if3tf0)다. 파일 세 개는 2026년 9월 16일 본인 저장소에서 AI 코딩 도구 Claude로 작성했다. 사용자 확인 기준 이후 파일 변경과 제3자 기여가 없고 라이선스 파일도 없다.

| 원본 파일 | 원본 커밋 | 실행 코드에서의 재사용 |
| --- | --- | --- |
| `legacy/ai/bot-detection-service/app/scoring.py` | `2b2dfd4` | `backend/app/adapters/bot_rules.py`로 바이트 그대로 복사. `bot_detection.py`에서 기존 함수에 근거 반환을 덧붙였다. |
| `legacy/ai/resale-monitor-service/app/crawler_client.py` | `eaaead6` | `resale_monitor.py`에서 HTTP 조회·응답 검사 로직을 비동기화하고 내부 피드와 리디렉션 미추적으로 설정했다. |
| `legacy/ai/resale-monitor-service/app/crawler.py` | `eaaead6` | `resale_monitor.py`에서 Beautiful Soup 선택자와 숫자 가격 정리를 재사용하고 누락 가격과 게시글 식별·본문·채널을 처리했다. |

세 파일의 기획서 SHA-256은 커밋에 저장된 원본에서 검증했다. 실행 어댑터, 데이터 변경, 화면과 검증 코드는 태그 뒤에 별도 커밋으로 남겼다.

## 6. 평가 결과

- Python 3.11.18 자동 검사 6개를 통과했다. 기존 점수와 신규 어댑터 1,000건이 일치했다.
- 기준 시드 80건이 실제 수집됐다. React 빌드에서 테스트 글 등록 후 81건 수집, 초기화 후 80건 복원과 실행 이력 삭제를 확인했다. 로컬 HTTP 수집 80건의 한 실행은 100ms였다.
- 추출 정확도·부정판매 탐지율·오탐률·군집 정확도·마스킹 누락·인젝션 방어율·모델 건당 시간과 비용은 T4~T6 구현 후 측정한다. 해당 지표의 실제 오답 3건은 아직 산출되지 않았다.

## 7. 화면 캡처 목록

가상 마켓의 초기 `post-017` 표시, 테스트 글 등록, 수집 81건 표시, 초기화 80건 복원까지 빌드된 React와 실제 로컬 API로 재현했다. 현재 화면 입력은 가상 게시글만 사용했다. Chromium 실행 환경의 소켓 제한으로 화면 이미지 캡처는 미완이다. 케이스·소명·재배분 화면은 후속 작업에서 캡처한다.

## 8. 알려진 오류와 한계

- 브라우저의 실제 렌더링과 레이아웃 점검은 남았다. React 동작은 DOM 실행 환경과 실제 Uvicorn 서버에서 검증했다.
- 데모 초기화는 같은 서버의 SQLite 상태 전체에 적용된다. 현재 로컬 데모는 접속자별 상태를 만들지 않는다.
- 감시는 HTTP 수집과 실행 로그까지 수행한다. 케이스 분석, 위험 판단, 승인형 조치 흐름은 아직 연결되지 않았다.

## 9. AI 사용 기록

Claude는 기획서를 갱신했고, 2026년 9월 사전 개발 파일 생성에 사용됐다. 형규님은 원본 저장소·브랜치·개발 이력·기여자·라이선스 상태와 오늘의 인수 기준을 확인했다. ChatGPT는 평가 시드 보완, 사전 개발 Git 기준점, 봇·수집 어댑터, SQLite·FastAPI, React 마켓, 검증 코드와 보고서를 작성했다.

## 10. 외부 자원 목록

| 자원 | 라이선스·출처 | 사용 위치 |
| --- | --- | --- |
| Python 3.11 | PSF License. [Python](https://docs.python.org/3/license.html) | 데이터 생성, 백엔드 |
| SQLite | 퍼블릭 도메인. [SQLite](https://www.sqlite.org/copyright.html) | 가상 데이터·실행 로그 저장 |
| FastAPI, Pydantic | MIT. [FastAPI](https://pypi.org/project/fastapi/) · [Pydantic](https://pypi.org/project/pydantic/) | API·입출력 검증 |
| Starlette, Uvicorn, httpx | BSD-3-Clause. [Starlette](https://pypi.org/project/starlette/) · [Uvicorn](https://pypi.org/project/uvicorn/) · [httpx](https://pypi.org/project/httpx/) | 비동기 API, 서버, 내부 HTTP 수집 |
| Beautiful Soup | MIT. [Beautiful Soup](https://pypi.org/project/beautifulsoup4/4.12.3/) | 수집 HTML 파싱 |
| React, React DOM, Vite | MIT. [React](https://github.com/facebook/react) · [Vite](https://github.com/vitejs/vite) | 마켓 화면과 빌드 |
| TypeScript | Apache-2.0. [TypeScript](https://github.com/microsoft/TypeScript) | 프론트 타입 검사 |
| 기존 TrueTicket 원본 | 사용자 본인 저장소, 별도 라이선스 파일 없음. [원본 브랜치](https://github.com/BAYERNA/TrueTicket/tree/claude/trueticket-workspace-if3tf0) | `legacy/`와 실행 어댑터 근거 |

공연·계정·예매·게시글·대기열은 생성기로 만든 가상 데이터다. 화면은 시스템 글꼴과 CSS를 사용한다.
