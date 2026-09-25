# verification-service는 로컬 개발 시 MinIO(S3 호환)에 얼굴 인증 캡처 이미지를
# AES-256-GCM으로 암호화해 저장한다(README 참고) — AWS에서는 실제 S3로 대체한다.
resource "aws_s3_bucket" "verification_snapshots" {
  bucket = "${local.name_prefix}-verification-snapshots"

  tags = { Name = "${local.name_prefix}-verification-snapshots" }
}

resource "aws_s3_bucket_public_access_block" "verification_snapshots" {
  bucket = aws_s3_bucket.verification_snapshots.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "verification_snapshots" {
  bucket = aws_s3_bucket.verification_snapshots.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# 캡처 이미지는 기본 30일 뒤 자동 삭제된다(README, SNAPSHOT_RETENTION_DAYS와 맞춘 기본값).
resource "aws_s3_bucket_lifecycle_configuration" "verification_snapshots" {
  bucket = aws_s3_bucket.verification_snapshots.id

  rule {
    id     = "expire-snapshots"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }
  }
}
