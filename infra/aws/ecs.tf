resource "aws_ecs_cluster" "main" {
  name = local.name_prefix

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${local.name_prefix}.local"
  vpc  = aws_vpc.main.id
}

resource "aws_service_discovery_service" "service" {
  for_each = merge(var.jvm_services, var.ai_services)

  name = each.key

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

resource "aws_cloudwatch_log_group" "service" {
  for_each = merge(var.jvm_services, var.ai_services)

  name              = "/ecs/${local.name_prefix}/${each.key}"
  retention_in_days = 30
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# 태스크 실행 역할이 Secrets Manager 값을 읽어 컨테이너 환경변수로 주입할 수 있어야 한다.
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${local.name_prefix}-secrets-read"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = concat(
        [aws_secretsmanager_secret.app.arn],
        [for s in aws_secretsmanager_secret.db : s.arn],
      )
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# verification-service만 얼굴 인증 캡처 이미지를 S3에 읽고 쓴다.
resource "aws_iam_role_policy" "verification_s3" {
  name = "${local.name_prefix}-verification-s3"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
      Resource = "${aws_s3_bucket.verification_snapshots.arn}/*"
    }]
  })
}

locals {
  # 모든 서비스가 공통으로 필요한 시크릿(JWT_SECRET 등).
  common_secrets = [
    { name = "JWT_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:JWT_SECRET::" },
    { name = "JWT_ISSUER", valueFrom = "${aws_secretsmanager_secret.app.arn}:JWT_ISSUER::" },
    { name = "INTERNAL_API_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:INTERNAL_API_KEY::" },
  ]

  # 서비스별 추가 시크릿(DB 접속 정보 등) — DB가 없는 서비스(discovery/gateway/queue)는 빈 목록.
  service_secrets = {
    discovery-service = []
    gateway-service = [
      { name = "GOOGLE_OAUTH_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.app.arn}:GOOGLE_OAUTH_CLIENT_ID::" },
    ]
    ticket-service = [
      { name = "SPRING_DATASOURCE_URL", valueFrom = "${aws_secretsmanager_secret.db["ticket-db"].arn}:url::" },
      { name = "SPRING_DATASOURCE_USERNAME", valueFrom = "${aws_secretsmanager_secret.db["ticket-db"].arn}:username::" },
      { name = "SPRING_DATASOURCE_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db["ticket-db"].arn}:password::" },
      { name = "PAYMENT_WEBHOOK_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:PAYMENT_WEBHOOK_SECRET::" },
      { name = "GOOGLE_OAUTH_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.app.arn}:GOOGLE_OAUTH_CLIENT_ID::" },
      { name = "GOOGLE_OAUTH_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.app.arn}:GOOGLE_OAUTH_CLIENT_SECRET::" },
    ]
    queue-service = [
      { name = "INTERNAL_ADMIT_API_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:INTERNAL_ADMIT_API_KEY::" },
    ]
    notification-service = [
      { name = "SPRING_DATASOURCE_URL", valueFrom = "${aws_secretsmanager_secret.db["notification-db"].arn}:url::" },
      { name = "SPRING_DATASOURCE_USERNAME", valueFrom = "${aws_secretsmanager_secret.db["notification-db"].arn}:username::" },
      { name = "SPRING_DATASOURCE_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db["notification-db"].arn}:password::" },
    ]
    bot-detection-service = [
      { name = "DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.db["bot-detection-db"].arn}:url_psycopg2::" },
    ]
    resale-monitor-service = [
      { name = "DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.db["resale-monitor-db"].arn}:url_psycopg2::" },
    ]
    verification-service = [
      { name = "DATABASE_URL", valueFrom = "${aws_secretsmanager_secret.db["verification-db"].arn}:url_psycopg2::" },
      { name = "SNAPSHOT_ENCRYPTION_KEY", valueFrom = "${aws_secretsmanager_secret.app.arn}:SNAPSHOT_ENCRYPTION_KEY::" },
    ]
  }

  # 서비스별 일반(비밀 아닌) 환경변수.
  common_env = {
    EUREKA_CLIENT_SERVICEURL_DEFAULTZONE = "http://discovery-service.${aws_service_discovery_private_dns_namespace.main.name}:8761/eureka/"
    TRACING_SAMPLE_RATE                  = "0.1"
  }
  service_env = {
    discovery-service = {}
    gateway-service = {
      FRONTEND_ORIGIN            = "https://trueticket.example.com"
      BOT_DETECTION_SERVICE_URI  = "http://bot-detection-service.${aws_service_discovery_private_dns_namespace.main.name}:8091"
      RESALE_MONITOR_SERVICE_URI = "http://resale-monitor-service.${aws_service_discovery_private_dns_namespace.main.name}:8092"
      VERIFICATION_SERVICE_URI   = "http://verification-service.${aws_service_discovery_private_dns_namespace.main.name}:8093"
      QUEUE_SOCKET_URI           = "http://queue-service.${aws_service_discovery_private_dns_namespace.main.name}:9092"
      SPRING_DATA_REDIS_HOST     = aws_elasticache_cluster.main.cache_nodes[0].address
    }
    ticket-service = {
      FRONTEND_ORIGIN           = "https://trueticket.example.com"
      PAYMENT_MOCK_ENABLED      = "false"
      BOT_DETECTION_SERVICE_URL = "http://bot-detection-service.${aws_service_discovery_private_dns_namespace.main.name}:8091"
    }
    queue-service = {
      SPRING_DATA_REDIS_HOST = aws_elasticache_cluster.main.cache_nodes[0].address
    }
    notification-service = {}
    bot-detection-service = {
      MODEL_VERSION = "bot-rules-v1"
    }
    resale-monitor-service = {
      MODEL_VERSION      = "resale-rules-v1"
      TICKET_SERVICE_URL = "http://ticket-service.${aws_service_discovery_private_dns_namespace.main.name}:8081"
    }
    verification-service = {
      TICKET_SERVICE_URL = "http://ticket-service.${aws_service_discovery_private_dns_namespace.main.name}:8081"
      S3_BUCKET          = aws_s3_bucket.verification_snapshots.bucket
    }
  }
}

resource "aws_ecs_task_definition" "service" {
  for_each = merge(var.jvm_services, var.ai_services)

  family                   = "${local.name_prefix}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = each.key
      image     = "${aws_ecr_repository.service[each.key].repository_url}:latest"
      essential = true
      portMappings = [{
        containerPort = each.value.port
        protocol      = "tcp"
      }]
      environment = [
        for k, v in merge(local.common_env, local.service_env[each.key]) : { name = k, value = v }
      ]
      secrets = concat(local.common_secrets, local.service_secrets[each.key])
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.service[each.key].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = each.key
        }
      }
    }
  ])
}

resource "aws_ecs_service" "service" {
  for_each = merge(var.jvm_services, var.ai_services)

  name            = each.key
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.service[each.key].arn
  desired_count   = each.value.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [for s in aws_subnet.private : s.id]
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  service_registries {
    registry_arn = aws_service_discovery_service.service[each.key].arn
  }

  dynamic "load_balancer" {
    # gateway-service만 ALB 대상 그룹에 등록한다 — 나머지는 Cloud Map을 통한
    # 서비스 간 통신만 필요하고 외부에 직접 노출되지 않는다.
    for_each = each.key == "gateway-service" ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.gateway.arn
      container_name   = each.key
      container_port   = each.value.port
    }
  }
}
