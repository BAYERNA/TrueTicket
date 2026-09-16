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

## 데이터 원칙

- **Database per Service**: 서비스별 PostgreSQL 인스턴스 분리, 물리적 FK 대신 ID 기반 논리적 참조
- 얼굴 인증 캡처 이미지는 DB가 아닌 **MinIO**(S3 호환)에 저장하고, DB에는 참조 경로만 보관
- 얼굴 임베딩·신분 정보 등 민감 정보는 AES-256 암호화 저장

## 로컬 개발 환경 실행

```bash
# 1. 인프라 기동 (PostgreSQL x5, Redis, Kafka, MinIO)
docker compose up -d

# 2. Core Domain 서비스 (각 디렉토리에서 개별 실행)
cd backend && ./gradlew :discovery-service:bootRun
cd backend && ./gradlew :gateway-service:bootRun
cd backend && ./gradlew :ticket-service:bootRun
cd backend && ./gradlew :queue-service:bootRun
cd backend && ./gradlew :notification-service:bootRun

# 3. AI Domain 서비스 (각 디렉토리에서 개별 실행)
cd ai/bot-detection-service && uvicorn app.main:app --reload --port 8091
cd ai/resale-monitor-service && uvicorn app.main:app --reload --port 8092
cd ai/verification-service && uvicorn app.main:app --reload --port 8093

# 4. 프론트엔드
cd frontend/web && npm install && npm run dev
```

## MVP 로드맵 (4주)

| 기간 | 범위 | 산출물 |
|---|---|---|
| 1주차 | 예매 코어 구축 | ticket-service, queue-service (가상대기열 동작) |
| 2주차 | 봇 탐지 1차 | 행동 로그 수집 → 규칙 기반 탐지 |
| 3주차 | 현장 검표 + AND 엔진 연동 | verification-service(YOLOv8 얼굴 인증) + Kafka 기반 판정 이력 저장(scam_judgments) |
| 4주차 | 재판매 모니터링 | resale-monitor-service 크롤링 MVP, 이상가격 대시보드 |

적용 범위(MVP): KBO 프로야구 티켓팅 → 이후 콘서트 등 공연 티켓으로 확장.
