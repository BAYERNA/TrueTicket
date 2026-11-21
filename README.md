# TicketGuard AI · 관객 및 운영자 통합 시연

외부 게시글을 내부 예매에 연결하고 운영자 승인 후 소명·취소·정가 재배분까지 처리하는 가상 데이터 해커톤 프로토타입이다. FastAPI·SQLite 단일 서버가 React 화면도 제공한다.

기본 실행은 **규칙 데모**다. API 키 없이 전체 처리 흐름을 시연할 수 있다. Gemini를 선택하면 마스킹한 가상 게시글을 실제 모델로 분석한다. 규칙 데모의 결과에는 `local_rules`를 표시한다.

## 관객과 운영자 연결

[공개 시연](https://ticketguard-ai-demo.tart-hippo-0446.chatgpt.site/)에서 세 가지 관객 점검 또는 한빛 콘서트의 검토 접수를 체험한다. 같은 운영자 브라우저로 접수함을 열어 접수번호와 두 좌석을 확인한다. 공개 공간은 합성 자료만 사용하며 원래 로컬 운영 DB와 별도로 시연 기록을 저장한다. 통합 접수함 코드는 [review-portal](review-portal/)에 있다. Python 관객 앱과 새로운 문장 10건의 실제 모델 대조 절차는 [audience/README.md](audience/README.md)에 있다.

## 실행

Python 3.11을 사용한다. 작업 ZIP에는 React 빌드가 들어 있다. README가 있는 폴더에서 실행한다.

Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe scripts/serve.py
```

macOS·Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python scripts/serve.py
```

[운영자 대시보드](http://127.0.0.1:8000/)에서 시작한다. `uvicorn backend.app.main:app` 한 줄로도 실행한다. `scripts/serve.py`는 호스팅의 `PORT`와 내부 HTTP 수집 포트를 맞춘다.

프론트를 고쳤다면 Node.js 20.19 이상(20.x) 또는 22.12 이상에서 다시 빌드한다.

```bash
npm --prefix frontend ci
npm --prefix frontend run build
```

## 기준 시연

1. 대시보드에서 `데모 초기화`, `에이전트 감시 시작`을 누른다. 분석 방식은 `규칙 데모`다.
2. 검색창에 `post-017`을 입력하고 케이스를 연다.
3. 외부 게시글과 예매 `booking-0001`·`booking-0002`, 장당 판매가 137,000원, 구입가 112,000원, 봇 점수 0.840, R1·R2·R4를 확인한다.
4. `소명 요청` 문서를 확인·수정하고 승인 체크 후 실행한다.
5. `소명 기한 경과` 후 `예매 취소·정가 재배분`을 승인한다. `fan-001`과 다음 R석 대기자 `fan-003`에게 장당 110,000원 안내가 나온다.
6. `신고서 초안`에서 문구를 수정하고 승인한다. `현재 신고서 내려받기`로 승인한 문서를 받는다. 승인 후 조치가 추가되면 수정한 문구 아래에 새 처리 이력과 정가 안내가 붙는다.

소명 도착 분기를 선택하면 취소가 차단된다. `정상 처리`로 닫으면 의심 케이스의 오탐 기록이 남는다. 정가 양도 `post-002`는 낮음, 가격 미상 `post-004`는 확인 불가다. 가상 마켓에 추가한 글도 다음 감시에서 수집된다. 장당 가격·수량·좌석을 제목 또는 본문에 쓰면 추출 근거를 확인할 수 있다. 별도 표시 가격은 마켓에 표시하는 값이다.

## Gemini 연결

추출 모델은 `gemini-3.5-flash-lite`, 임베딩은 `gemini-embedding-001`이다. 무료 등급 지원과 본인의 프로젝트 한도를 확인한다. [모델](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) · [무료 등급](https://ai.google.dev/gemini-api/docs/pricing) · [호출 한도](https://ai.google.dev/gemini-api/docs/rate-limits)

PowerShell에서 키를 현재 세션 환경변수에 설정한 뒤 서버를 시작한다.

```powershell
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Gemini API key" -AsSecureString)).Password
.\.venv\Scripts\python.exe scripts/serve.py
```

Bash에서는 현재 세션에 입력한다.

```bash
read -rsp 'Gemini API key: ' GEMINI_API_KEY
export GEMINI_API_KEY
python scripts/serve.py
```

키를 설정해도 기본 감시는 규칙 데모로 열리며 외부 모델 호출은 0건이다. 실제 모델을 쓸 때 대시보드에서 `Gemini 분석`을 선택한다. 요청 한도나 연결 문제로 추출·임베딩이 중단되면 기존 케이스를 보존하고 실패 단계를 표시한다. 다음 Gemini 감시는 성공한 추출부터 재사용한다. 설명 문장만 생성하지 못한 경우에는 규칙 설명을 표시하고 부분 완료로 기록한다. 기존 OpenAI A안의 평가 CLI `backend.app.evaluation.t4`는 별도로 실행할 때 OpenAI API를 사용한다.

| 환경변수 | 기본값과 동작 |
| --- | --- |
| `GEMINI_API_KEY` | Gemini 비밀 키. `GOOGLE_API_KEY`도 지원한다. |
| `TRUETICKET_DAILY_REQUEST_LIMIT` | UTC 날짜당 100회. SQLite에 예약하며 데모 초기화 후에도 누적된다. |
| `TRUETICKET_REQUEST_INTERVAL` | Gemini 요청 간 12초. 실제 프로젝트 한도에 맞춰 조정한다. |
| `TRUETICKET_DB` | 기본 `data/demo.sqlite3`. 승인 체크포인트도 같은 SQLite를 쓴다. |
| `PORT` | `scripts/serve.py`의 기본 포트 8000. 내부 피드도 같은 포트다. |

## 평가

대시보드의 `평가셋 검증`은 선택한 방식으로 독립 SQLite에서 80건을 평가한다. GET `/api/eval`은 최근 집계, POST `/api/eval`은 평가 시작 경로다.

```bash
python -m unittest discover -s backend/tests -v
python -m backend.app.evaluation.full --mode local
python -m backend.app.evaluation.full --mode gemini
```

Gemini 평가는 외부 API를 호출한다. 성공한 추출은 `data/evaluation/gemini_progress.json`에 저장해 다음 평가에서 재사용한다. 한도가 복구된 뒤 같은 명령으로 이어간다. 결과에 재사용 건수와 이번 실행에서 새로 전송한 요청·토큰·시간을 기록한다.

`local_results.json`과 `gemini_results.json`은 별도 파일이다. `validation_scope`가 `local_rules`이면 AI 인수 기준 충족은 `false`다. 정답은 평가 모듈만 읽고 일반 분석 그래프와 마켓은 읽지 않는다.

## 배포 준비

Dockerfile은 Python 3.11 단일 서버와 React 빌드를 담는다. Python 프로세스와 쓰기 가능한 SQLite 경로를 지원하는 호스팅이 필요하다. 공개 배포와 로그아웃 접근 점검은 남아 있다. 현재 환경에는 Docker 엔진이 없어 이미지 빌드는 미검증이다.

한 서버의 가상 상태를 공유한다. 초기화는 케이스·예매·대기열과 승인 체크포인트를 함께 복원한다. 서버 재시작 때 SQLite 파일을 보존하면 승인 대기와 사용량도 이어진다.

## Credits / Licenses

사전 개발 원본은 [BAYERNA/TrueTicket 작업 브랜치](https://github.com/BAYERNA/TrueTicket/tree/claude/trueticket-workspace-if3tf0)의 2026년 9월 16일 Claude 작성 파일 3개다. 사용자 확인 기준 제3자 기여와 별도 라이선스 파일은 없다. 원문은 `pre-hackathon` 태그의 `7237a53`에 있고 SHA-256은 기존 보고서와 같다.

모델·패키지·라이선스·검증 상태는 [11월 19일 보고서](docs/TrueTicket_Claude_handoff_2026-11-19.md)에 정리했다. ZIP의 `TrueTicket.git.bundle`은 개발 커밋과 태그를 포함한다. `git clone ./TrueTicket.git.bundle trueticket-history`로 이력을 복원한다.
