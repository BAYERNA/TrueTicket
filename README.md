# TrueTicket

예매 → 재판매 → 입장까지, 티켓의 전 생애주기에서 암표(부정거래)를 차단하는 MSA 기반 검증 플랫폼.

가격만으로 암표를 판단하지 않고, **취득 부정성 스코어**(예매 단계 매크로/봇 탐지)와
**상습 판매 스코어**(유통 단계 재판매 이상탐지)를 각각 산출한 뒤, 두 스코어가 모두 임계치를
초과할 때만 최종 판정하는 **AND 엔진**으로 선의의 이용자 오탐을 최소화한다.

## 아키텍처

Eureka(서비스 디스커버리) + Spring Cloud Gateway(단일 진입점) 위에서, 트랜잭션 안정성이
필요한 Core Domain은 Kotlin/Spring Boot(동기 호출, OpenFeign+Resilience4j)로, 비동기·ML·CV
연산이 필요한 AI Domain은 FastAPI로 분리했다. 즉시 응답이 필요한 흐름은 Orchestration,
시점이 독립적인 AND 엔진 조인은 Kafka 기반 Choreography로 처리하는 하이브리드 패턴이다.

```
backend/                Kotlin + Spring Boot (Core Domain, Gradle 멀티 프로젝트)
├── discovery-service    Eureka 서비스 디스커버리
├── gateway-service       Spring Cloud Gateway (라우팅 · Rate Limiting)
├── ticket-service         예매 · 좌석 · 주문 (JPA Optimistic Lock, PostgreSQL)
├── queue-service           가상 대기열 (Redis)
└── notification-service    신고 · 알림 · AND 엔진 최종 판정(scam_judgments) 저장

ai/                     FastAPI (AI Domain, 서비스별 독립 배포)
├── bot-detection-service    예매 단계 행동 기반 이상탐지 → 취득 부정성 스코어
├── resale-monitor-service   재판매 플랫폼 크롤링 · 가격 이상탐지 → 상습 판매 스코어
└── verification-service     현장 검표 · YOLOv8 얼굴 본인인증

frontend/web            React · Next.js (예매 웹 · 운영자 대시보드)
mobile/verification-app Flutter (현장 검표 앱)
```

## 서비스 간 통신

| 흐름 | 방식 | 비고 |
|---|---|---|
| Core Domain 내부 동기 호출 | OpenFeign + Resilience4j | 즉시 응답이 필요한 예매↔봇탐지 등 |
| AND 엔진 스코어 조인 | Kafka | bot-detection-service·resale-monitor-service → notification-service |
| 외부 요청 진입점 | Spring Cloud Gateway | Rate Limiting으로 대기열 진입 전 1차 방어 |
| 서비스 디스커버리 | Eureka | Client-side Service Discovery |

사용자 요청은 ticket-service가 발급한 HS256 JWT로 인증하며, Gateway와 각 서비스가
동일한 issuer·서명을 다시 검증한다. `USER`, `STAFF`, `ADMIN` 역할을 구분하고 사용자별
예매·신고·알림 API는 JWT의 `sub`를 사용하므로 요청 본문으로 다른 사용자 ID를 위조할 수 없다.
서비스 간 호출은 별도의 `X-Internal-Api-Key`로 보호한다.

Kafka의 at-least-once 전달로 같은 이벤트가 재전송돼도
`(reservation_session_id, listing_id)` 유니크 인덱스와 `ON CONFLICT DO NOTHING`으로
최종 판정을 한 번만 저장한다. 한쪽 스코어만 도착한 미완성 조인 버퍼는 기본 24시간 후
정리되며, 보관 시간과 정리 주기는 환경 설정으로 변경할 수 있다.
AI 서비스는 판정 데이터와 Kafka 이벤트를 같은 DB 트랜잭션의 outbox에 기록한다. 발행 실패는
지수 백오프로 재시도하고 5회 실패 시 `DEAD`로 격리하며, 소비 실패는 원 토픽의 `.DLT`로 이동한다.

## 데이터 원칙

- **Database per Service**: 서비스별 PostgreSQL 인스턴스 분리, 물리적 FK 대신 ID 기반 논리적 참조
- 얼굴 인증 캡처 이미지는 AES-256-GCM으로 암호화해 **MinIO**에 저장하고, 기본 30일 뒤 자동 삭제
- 좌석은 기본 5분간만 선점되며 결제 성공 후에만 QR을 발급; 실패·만료·취소 시 자동 반환

## 로컬 개발 환경 실행

```bash
# 1. 필수 비밀값 설정(예시 값 그대로 운영 환경에 사용하지 말 것)
export JWT_SECRET='replace-with-at-least-32-random-bytes'
export INTERNAL_API_KEY='replace-with-a-random-internal-key'
export PAYMENT_WEBHOOK_SECRET='replace-with-a-random-webhook-secret'
export PAYMENT_MOCK_ENABLED=true

# 2. 인프라 기동 (PostgreSQL x5, Redis, Kafka, MinIO, Prometheus, Tempo, Grafana)
docker compose up -d

# 3. Core Domain 서비스 (각 디렉토리에서 개별 실행)
cd backend && ./gradlew :discovery-service:bootRun
cd backend && ./gradlew :gateway-service:bootRun
cd backend && ./gradlew :ticket-service:bootRun
cd backend && ./gradlew :queue-service:bootRun
cd backend && ./gradlew :notification-service:bootRun

# 4. AI Domain 서비스 (각 서비스의 .env.example을 .env로 복사하고 비밀값 교체)
# 시작 시 Alembic이 미적용 DB 마이그레이션을 자동 반영한다.
cd ai/bot-detection-service && uvicorn app.main:app --reload --port 8091
cd ai/resale-monitor-service && uvicorn app.main:app --reload --port 8092
cd ai/verification-service && uvicorn app.main:app --reload --port 8093

# 5. 프론트엔드
cd frontend/web && npm install && npm run dev
```

### AI Domain 스키마 마이그레이션

세 FastAPI 서비스는 `create_all()` 대신 Alembic으로 스키마를 버전 관리한다. 서비스 시작 시
`upgrade head`가 실행되므로 기존 DB에도 새 컬럼과 인덱스가 반영된다. 배포 전에 별도로
검증하거나 롤백해야 할 때는 각 서비스 디렉터리에서 다음 명령을 사용한다.

```bash
alembic current
alembic upgrade head
alembic downgrade -1
```

## 관찰성 (Prometheus + OpenTelemetry + Tempo + Grafana)

Core Domain 5개 서비스는 Micrometer로 `GET /actuator/prometheus`를, AI Domain 3개
서비스는 `prometheus-fastapi-instrumentator`로 `GET /metrics`를 노출한다.
`docker compose up -d`로 인프라와 함께 Prometheus·Grafana도 올라간다(Prometheus는
`host.docker.internal`로 호스트에서 직접 실행 중인 8개 서비스를 스크레이프한다).
Spring과 FastAPI 서비스의 분산 trace는 OTLP/HTTP로 Tempo에 전송되며 Grafana Explore에서
서비스 간 요청과 DB 호출을 하나의 trace로 조회할 수 있다.

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (기본 계정 admin/admin, 익명 뷰어 접근 허용) —
  `TrueTicket — 서비스 개요` 대시보드가 자동 프로비저닝되어 서비스 UP 상태, 요청
  처리량, 평균 지연시간, JVM 힙 메모리를 보여준다.

## 검증

```bash
cd backend && ./gradlew test
cd frontend/web && npm ci && npm run lint && npm run build
```

백엔드 CI는 Testcontainers로 실제 PostgreSQL 16에 Flyway 마이그레이션과 주요 제약을 검증하고,
AI 서비스 CI는 각 Alembic revision을 실제 PostgreSQL에서 upgrade/downgrade한다.

## MVP 로드맵 (4주)

| 기간 | 범위 | 산출물 |
|---|---|---|
| 1주차 | 예매 코어 구축 | ticket-service, queue-service (가상대기열 동작) |
| 2주차 | 봇 탐지 1차 | 행동 로그 수집 → 규칙 기반 탐지 |
| 3주차 | 현장 검표 + AND 엔진 연동 | verification-service(YOLOv8 얼굴 인증) + Kafka 기반 판정 이력 저장(scam_judgments) |
| 4주차 | 재판매 모니터링 | resale-monitor-service 크롤링 MVP, 이상가격 대시보드 |

적용 범위(MVP): KBO 프로야구 티켓팅 → 이후 콘서트 등 공연 티켓으로 확장.
