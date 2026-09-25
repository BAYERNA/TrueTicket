# JWT_SECRET/INTERNAL_API_KEY/PAYMENT_WEBHOOK_SECRET처럼 애플리케이션이 스스로
# 검증만 하고 사람이 직접 알 필요는 없는 값은 Terraform이 생성해 Secrets Manager에
# 저장한다. Google OAuth2 클라이언트 자격증명은 Google Cloud Console에서 발급받아야
# 하는 값이라 Terraform이 대신 만들 수 없다 — 변수로 주입한다(terraform.tfvars.example 참고).

resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

resource "random_password" "internal_api_key" {
  length  = 32
  special = false
}

resource "random_password" "internal_admit_api_key" {
  length  = 32
  special = false
}

resource "random_password" "payment_webhook_secret" {
  length  = 32
  special = false
}

variable "google_oauth_client_id" {
  description = "Google Cloud Console에서 발급받은 OAuth2 클라이언트 ID (플레이스홀더면 실제 로그인은 완료되지 않는다)"
  type        = string
  default     = "placeholder-google-client-id"
  sensitive   = true
}

variable "google_oauth_client_secret" {
  description = "Google Cloud Console에서 발급받은 OAuth2 클라이언트 시크릿"
  type        = string
  default     = "placeholder-google-client-secret"
  sensitive   = true
}

variable "sentry_dsn" {
  description = "Sentry 프로젝트 DSN (비워두면 프론트엔드/백엔드 모두 조용히 비활성 상태로 동작)"
  type        = string
  default     = ""
  sensitive   = true
}

resource "aws_secretsmanager_secret" "app" {
  name = "${local.name_prefix}/app"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    JWT_SECRET                 = random_password.jwt_secret.result
    JWT_ISSUER                 = "trueticket"
    INTERNAL_API_KEY           = random_password.internal_api_key.result
    INTERNAL_ADMIT_API_KEY     = random_password.internal_admit_api_key.result
    PAYMENT_WEBHOOK_SECRET     = random_password.payment_webhook_secret.result
    GOOGLE_OAUTH_CLIENT_ID     = var.google_oauth_client_id
    GOOGLE_OAUTH_CLIENT_SECRET = var.google_oauth_client_secret
    SENTRY_DSN                 = var.sentry_dsn
  })
}
