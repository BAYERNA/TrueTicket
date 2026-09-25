output "alb_dns_name" {
  description = "gateway-service로 향하는 ALB DNS 이름 — 프론트엔드의 NEXT_PUBLIC_API_BASE_URL로 쓴다"
  value       = aws_lb.main.dns_name
}

output "ecr_repository_urls" {
  description = "서비스별 ECR 저장소 URL — CI/CD에서 이미지를 푸시할 때 쓴다"
  value       = { for name, repo in aws_ecr_repository.service : name => repo.repository_url }
}

output "rds_endpoints" {
  description = "서비스별 RDS 엔드포인트"
  value       = { for name, db in aws_db_instance.service : name => db.endpoint }
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis 엔드포인트"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "verification_snapshots_bucket" {
  description = "verification-service가 얼굴 인증 캡처 이미지를 저장하는 S3 버킷"
  value       = aws_s3_bucket.verification_snapshots.bucket
}

output "app_secrets_arn" {
  description = "JWT_SECRET 등 공통 애플리케이션 시크릿이 저장된 Secrets Manager ARN"
  value       = aws_secretsmanager_secret.app.arn
}
