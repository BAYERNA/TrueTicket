# AWS Terraform (참고용 — 실제로 배포된 적 없음)

TrueTicket의 8개 애플리케이션 서비스를 ECS Fargate로 배포할 때의 출발점이 되는
참고 Terraform 구성이다. **실제 AWS 계정에 적용된 적은 없다.** 이 샌드박스에는 AWS
자격증명이 없어서, 진짜로 검증할 수 있는 한계까지 검증했다:

- `terraform validate` 통과 (문법 + 타입 + 참조 정합성)
- `terraform plan`을 실제로 실행해, `random_password` 리소스 9개는 계획을 완료했고
  — AWS API 호출이 필요한 첫 리소스(`GetCallerIdentity`)에서 정확히 자격증명
  오류(`InvalidClientTokenId`)로 멈추는 것까지 확인했다. 즉 전체 리소스 그래프(모든
  `for_each`, `jsonencode`, 리소스 간 참조)가 실제로 풀린다는 뜻이다 — AWS 계정만
  있으면 그 다음부터 진행된다.
- `terraform fmt -check` 통과

실행 과정에서 실제 버그도 하나 발견해 고쳤다: AWS 보안 그룹의 `ingress.description`
필드는 ASCII만 허용하는데, 처음에는 한글 설명을 넣어서 `terraform validate`가
막았다 — 이 디렉터리의 `security_groups.tf`만 영문 설명을 쓰는 이유다.

## 아키텍처

```
Internet -> ALB (public subnet) -> gateway-service (ECS Fargate, private subnet)
                                       -> Cloud Map(trueticket.local)으로 나머지 7개 서비스 탐색
5개 RDS PostgreSQL(서비스별 1개, Database per Service) — private subnet
ElastiCache Redis(gateway rate limiting + queue-service 가상대기열 공유) — private subnet
S3(verification-service 얼굴 인증 캡처, 30일 후 자동 만료)
Secrets Manager(JWT_SECRET 등은 Terraform이 자동 생성, DB 비밀번호도 자동 생성)
ECR(서비스별 저장소, 최근 10개 이미지만 보관)
```

## 여기 없는 것

- **Kafka**: MSK 등은 포함하지 않았다 — 별도 모듈이나 관리형 서비스로 준비해야 한다.
- **컨테이너 이미지**: 모든 ECS 태스크 정의는 `<ECR 저장소>:latest`를 가리키는데,
  이 이미지들은 실제로 빌드/푸시된 적이 없다. CI/CD에서 각 서비스의 `Dockerfile`로
  빌드해 `terraform output ecr_repository_urls`가 알려주는 저장소로 푸시해야 한다.
- **프론트엔드**: Next.js 앱은 Dockerfile이 없다 — Vercel 등이 일반적인 배포 대상이라
  여기 포함하지 않았다(k8s/README.md와 동일한 이유).
- **도메인/ACM 인증서**: `acm_certificate_arn`을 비워두면 HTTP(80)로만 서비스한다.
  운영 배포에는 실제 도메인과 ACM 인증서가 필요하다.

## 실제로 적용하려면

```bash
cd infra/aws
terraform init

cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars에 실제 Google OAuth2 자격증명, Sentry DSN, ACM 인증서 ARN 등을 채운다.

terraform plan
terraform apply
```

JWT_SECRET, INTERNAL_API_KEY, PAYMENT_WEBHOOK_SECRET, DB 비밀번호는 Terraform이
`random_password`로 직접 생성해 Secrets Manager에 저장하므로 따로 채울 필요가 없다.
Google OAuth2 클라이언트 자격증명만 Google Cloud Console에서 발급받아 변수로
주입해야 한다 — 비워두면(기본값) `/oauth2/authorization/google` 리다이렉트 자체는
여전히 시도되지만 실제 로그인은 완료되지 않는다(README 루트 문서의 설명과 동일).

## Kubernetes 매니페스트와의 관계

같은 애플리케이션을 대상으로 한 두 가지 서로 다른 배포 방식이다 — 실제 운영에서는
둘 중 하나만 고르면 된다. `k8s/`가 다루지 않는 것(Ingress/TLS, 관리형 인프라 선택 등)을
이 Terraform 구성이 AWS 네이티브 방식(ALB, RDS, ElastiCache, ECS Fargate, Secrets
Manager)으로 보여준다.
