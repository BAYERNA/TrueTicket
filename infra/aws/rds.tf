locals {
  # Database per Service — 서비스별로 독립된 PostgreSQL 인스턴스를 둔다
  # (docker-compose.yml/README의 "Database per Service" 원칙과 동일).
  databases = {
    ticket-db = {
      db_name  = "ticket_service"
      username = "ticket"
    }
    notification-db = {
      db_name  = "notification_service"
      username = "notification"
    }
    bot-detection-db = {
      db_name  = "bot_detection_service"
      username = "botdetect"
    }
    resale-monitor-db = {
      db_name  = "resale_monitor_service"
      username = "resale"
    }
    verification-db = {
      db_name  = "verification_service"
      username = "verify"
    }
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db"
  subnet_ids = [for s in aws_subnet.private : s.id]

  tags = { Name = "${local.name_prefix}-db" }
}

resource "random_password" "db" {
  for_each = local.databases

  length  = 24
  special = false
}

resource "aws_db_instance" "service" {
  for_each = local.databases

  identifier     = "${local.name_prefix}-${each.key}"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = each.value.db_name
  username = each.value.username
  password = random_password.db[each.key].result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period   = 7
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name_prefix}-${each.key}-final"
  deletion_protection       = true
  publicly_accessible       = false

  tags = { Name = "${local.name_prefix}-${each.key}" }
}

# 각 DB 접속 정보를 Secrets Manager에 저장한다 — ECS 태스크 정의가 secretKeyRef로 참조한다.
resource "aws_secretsmanager_secret" "db" {
  for_each = local.databases

  name = "${local.name_prefix}/${each.key}"
}

resource "aws_secretsmanager_secret_version" "db" {
  for_each = local.databases

  secret_id = aws_secretsmanager_secret.db[each.key].id
  secret_string = jsonencode({
    url = "jdbc:postgresql://${aws_db_instance.service[each.key].endpoint}/${each.value.db_name}"
    # FastAPI 서비스(SQLAlchemy)는 JDBC가 아니라 psycopg2 URL 형식을 쓴다.
    url_psycopg2 = "postgresql+psycopg2://${each.value.username}:${random_password.db[each.key].result}@${aws_db_instance.service[each.key].endpoint}/${each.value.db_name}"
    username     = each.value.username
    password     = random_password.db[each.key].result
  })
}
