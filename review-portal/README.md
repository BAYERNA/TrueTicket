# TicketGuard AI
관객용 세 가상 사례와 한빛 콘서트 통합 시연. 운영자 공간을 개설하고 관객 링크에서 근거를 선택해 접수한 뒤 접수번호를 원래 운영자 브라우저에서 대조한다. 시연용 개인 공간과 세션만 발급한다. 실제 예매·신고·메시지 발송과 연결되지 않는다.

## 실행 및 확인
Node 22.13 이상에서 `bash scripts/build.sh && node scripts/validate-artifact.mjs && node --test tests/flow.mjs`. 배포에는 Cloudflare Worker ES 모듈, D1 바인딩 DB 및 drizzle/0000_review.sql이 필요하다. 저장 데이터는 시연 공간, 선택 근거 인덱스·접수번호, 모의 처리 단계, 정가 구매 안내다. 소명 도착과 기한 경과는 운영자 화면에서 재현한다.

## 기준 자료
세 관객 결과는 TicketGuard AI 01–08 실행본의 seed 및 Python analyze 함수에서 산출했다. 한빛 fixture는 BAYERNA/TrueTicket f643f52의 data/seed.json, docs/sample-report.txt, 관객 앱 integration/hanbit_example.json을 사용한다. 공개 프리셋은 생성형 AI를 호출하지 않는다.
