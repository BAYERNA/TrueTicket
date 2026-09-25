# Kubernetes manifests (참고용 — 실제로 배포되어 있지 않음)

이 디렉터리는 TrueTicket의 8개 애플리케이션 서비스(Core Domain 5개 + AI Domain 3개)를
쿠버네티스에 배포할 때의 출발점이 되는 참고 매니페스트다. **실제 클러스터에 적용된
적은 없다** — 이 샌드박스에는 실행 중인 쿠버네티스 클러스터가 없어서, `kubectl apply
--dry-run=client`로 문법과 스키마만 검증했다.

## 여기 없는 것

- **Kafka, Redis, MinIO, PostgreSQL 5개**: 이 매니페스트는 애플리케이션 레이어만
  다룬다. 실제 배포에서는 관리형 서비스(RDS, ElastiCache, MSK 등)나 검증된 Helm
  차트(Bitnami postgresql/redis/kafka 등)를 쓰는 것을 권장한다 — Postgres/Kafka를
  직접 StatefulSet으로 운영하는 건 이 매니페스트의 범위를 넘어선다.
- **Ingress/TLS**: gateway-service의 Service는 ClusterIP다. 외부 노출은 클러스터마다
  다른 Ingress 컨트롤러/인증서 방식에 맞춰 별도로 구성해야 한다.
- **컨테이너 이미지**: 모든 Deployment는 `ghcr.io/trueticket/<service>:latest`를
  가리키는데, 이 이미지들은 실제로 빌드/푸시된 적이 없는 자리표시자다. 실제 배포
  전에는 각 서비스의 `Dockerfile`(backend/*, ai/*)로 빌드해 실제 레지스트리에 푸시한
  이미지로 교체해야 한다.
- **프론트엔드**: Next.js 앱은 이 저장소에 Dockerfile이 없다 — Vercel 같은 플랫폼이
  일반적인 배포 대상이라 여기 포함하지 않았다.

## 실제로 적용하려면

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# secret.yaml.example을 복사해 실제 비밀값으로 교체한 뒤 적용 (secret.yaml은 gitignore됨)
cp k8s/secret.yaml.example k8s/secret.yaml
# ... 값 교체 ...
kubectl apply -f k8s/secret.yaml

kubectl apply -f k8s/discovery-service.yaml
kubectl apply -f k8s/gateway-service.yaml
kubectl apply -f k8s/ticket-service.yaml
kubectl apply -f k8s/queue-service.yaml
kubectl apply -f k8s/notification-service.yaml
kubectl apply -f k8s/bot-detection-service.yaml
kubectl apply -f k8s/resale-monitor-service.yaml
kubectl apply -f k8s/verification-service.yaml
```

## 환경변수 오버라이드 방식

Spring Boot 서비스(discovery/gateway/ticket/queue/notification)는 각 `application.yml`에
`${ENV_VAR:default}` 형태로 이미 써둔 값도 있고, 그렇지 않은 하드코딩된 값(예:
`eureka.client.service-url.defaultZone: http://localhost:8761/eureka/`)도 있다.
후자도 Spring Boot의 relaxed binding 덕분에 환경변수가 자동으로 우선하므로
(`EUREKA_CLIENT_SERVICEURL_DEFAULTZONE` 등), 소스 코드를 건드리지 않고도
`configmap.yaml`/`secret.yaml`만으로 클러스터 환경에 맞게 오버라이드했다.

FastAPI 서비스(bot-detection/resale-monitor/verification)는 각 서비스의
`.env.example`과 동일한 이름의 환경변수를 pydantic-settings로 그대로 읽는다.

배포 전에 각 서비스의 `application.yml`/`.env.example`을 한 번 더 확인해, 여기
매니페스트가 다루지 않는 서비스별 옵션(재시도 간격, 서킷브레이커 설정 등)이
운영 환경에 맞는지 점검하는 것을 권장한다.
