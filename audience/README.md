# TicketGuard AI

공연·스포츠 티켓에 송금하기 전에 판매 글, 가상 기준가, 양도 정책을 대조하는 관객용 MVP다. 원본 설계서 01~08과 검토보고서의 V1.0 기준으로 재구현했다.

## 실행

Python 3.10~3.12 환경에서 이 README가 있는 폴더를 연다. 아래는 macOS·Linux용 명령이다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

공연 또는 스포츠를 고르고 시연 사례를 선택한다. 가상 게시글임을 확인한 뒤 ‘분석 시작’을 누르면 네 구획이 표시된다. ‘TXT 진단 결과 다운로드’로 결과를 저장할 수 있다.

| 시연 사례 | 장당 제시액 | 가상 기준가 | 기대 결과 |
| --- | ---: | ---: | --- |
| 별빛 페스티벌 | 300,000원 | 120,000원 | CAUTION · +180,000원, +150.0% |
| 뮤지컬 밤의 서약 | 110,000원 | 110,000원 | CAUTION · 캡처 입장 제한 |
| 시티 블루스 vs 리버 레즈 | 60,000원 | 60,000원 | REVIEW · 공식 선물하기 확인 |

## 자료와 판단 방식

- 기본 모드는 3가지 가상 게시글에 대응하는 사전 추출값을 읽는다. 직접 입력하거나 수정한 문장에 기존 샘플 가격을 적용하지 않는다.
- `src/privacy.py`에서 빈 입력과 전화·이메일·계좌번호 의심 패턴을 검사한다. 패턴 검사는 완전한 비식별 처리를 보장하지 않으므로 가상 입력만 사용한다.
- 선택형 모델 추출은 `OPENAI_API_KEY`와 UI 선택이 모두 필요하다. 셸 환경변수 또는 Streamlit Secrets에 설정한다. `.env.example`은 변수명 예시이며 키를 포함하지 않는다. `OPENAI_MODEL`을 설정하면 기본 모델명(gpt-4o-mini)을 바꿀 수 있다.
- `src/repository.py`가 SQLite 테이블을 초기화하고 `data/demo_seed.json`에서 시드를 넣는다. 기본 카탈로그는 운영체제 임시 폴더에 생성된다. 다른 위치는 `TICKETGUARD_DB_PATH`로 지정할 수 있다. 분석 결과와 자유 입력 원문은 DB에 저장하지 않는다.
- 사례명·좌석·가격·양도 조건은 원본 문서의 가상값을 따랐다. 시험에 필요한 뮤지컬·야구 날짜, 행사장, 게시글 문구는 시연용으로 보충했다. 행사의 실제 약관이나 관람 권한을 입증하는 자료가 아니다.
- 모든 결과에 `NOT_DETERMINED`를 유지한다. 공식 신고센터는 사용자가 링크로 방문한다.

## 검증 기록

Python 3.12.14, Streamlit 1.67.0, OpenAI SDK 2.54.0에서 핵심 단위 테스트 17개와 Streamlit AppTest 5개를 통과했다. AppTest는 위젯에서 세 사례를 분석해 다운로드 버튼에 공급된 UTF-8 본문을 검사한다. 이 결과의 범위는 로컬 앱 테스트다. 공개 URL/모바일 브라우저에서의 실제 파일 저장, 실제 LLM 호출과 필드 일치율, 최종 제출 증빙은 후속 점검 항목이다.

## 한빛 콘서트와 운영자 연계

`integration/hanbit_example.json`은 기존 운영자 데모의 가상 게시글 post-017을 기준으로 공개 요청 항목과 담당 운영자용 기대값을 표시한 계약 예시다. 선택 전송부터 접수번호 대조, 운영자 세션 확인, 소명과 정가 구매 안내까지의 실행 코드는 저장소의 review-portal에 있다. 전체 예시 파일은 개발용이며 관객에게 전달할 응답으로 사용하지 않는다. 관객용 앱에는 원본의 세 사례만 등록한다.

운영자 원자료는 [TrueTicket 가상 시연 보고서](https://github.com/BAYERNA/TrueTicket/blob/f643f52dd0103299619a1c31a359a6f9e1191f71/docs/sample-report.txt)에서 확인할 수 있다.

## 가상 한빛 사건과 실제 모델 대조
공개 관객·운영 시연은 https://ticketguard-ai-demo.tart-hippo-0446.chatgpt.site/ 에서 실행한다. 운영자 시연 공간을 개설하면 관객 초대 주소의 `w` 값이 정해진다. 같은 `?w=<시연 공간 UUID>`로 이 Streamlit 앱을 열면 한빛 접수 폼이 해당 공간의 서버에 전송하며 같은 접수번호를 표시한다.

이 폴더에서 `python evaluation/live_check.py --output live_result.json`을 실행하면 기존 관객 앱의 실제 OpenAI 추출 경로로 신규 합성 문장 10건을 검증한다. 환경변수 OPENAI_API_KEY가 필요하다. OPENAI_MODEL로 사용할 모델을 선택할 수 있다. 키가 없으면 실행 보류를 기록하고 종료한다. 필드 정확도는 10건 모두 처리한 경우에만 산출한다.
