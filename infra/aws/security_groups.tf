# AWS 보안 그룹의 description 필드는 ASCII 문자만 허용한다(정규식 제약) — 이 파일의
# description 값들은 한글 대신 영문으로 쓴다. 그 외 주석은 이 저장소의 다른 파일과
# 동일하게 한글로 남긴다.

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb"
  description = "Receives inbound internet traffic for the ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP (redirected to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-alb" }
}

# ECS 태스크 — ALB에서만 인바운드를 받고, 서비스 간 통신은 같은 SG 내부에서 전부 허용한다.
resource "aws_security_group" "ecs_tasks" {
  name        = "${local.name_prefix}-ecs-tasks"
  description = "ECS tasks - accepts inbound only from the ALB, plus inter-service traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "ALB -> gateway-service"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-ecs-tasks" }
}

# ECS 태스크끼리의 서비스 간 호출(Eureka 등록/조회, OpenFeign 호출 등)을 허용한다.
resource "aws_security_group_rule" "ecs_tasks_self" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs_tasks.id
  source_security_group_id = aws_security_group.ecs_tasks.id
}

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-rds"
  description = "PostgreSQL - accessible only from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "ECS tasks -> PostgreSQL"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-rds" }
}

resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis"
  description = "ElastiCache Redis - accessible only from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "ECS tasks -> Redis"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-redis" }
}
