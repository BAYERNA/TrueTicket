variable "aws_region" {
  description = "배포할 AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "환경 이름(리소스 이름/태그에 사용)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR 블록"
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "사용할 가용 영역 2개"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
}

# ---------------------------------------------------------------------------
# 애플리케이션 서비스 정의 — docker-compose.yml/k8s/*.yaml과 동일한 포트를 쓴다.
# ---------------------------------------------------------------------------

variable "jvm_services" {
  description = "Core Domain(Kotlin/Spring) 서비스 — 이름, 컨테이너 포트, health check 경로"
  type = map(object({
    port          = number
    health_path   = string
    cpu           = number
    memory        = number
    desired_count = number
  }))
  default = {
    discovery-service = {
      port          = 8761
      health_path   = "/actuator/health"
      cpu           = 512
      memory        = 1024
      desired_count = 1
    }
    gateway-service = {
      port          = 8080
      health_path   = "/actuator/health"
      cpu           = 512
      memory        = 1024
      desired_count = 2
    }
    ticket-service = {
      port          = 8081
      health_path   = "/actuator/health"
      cpu           = 512
      memory        = 1024
      desired_count = 2
    }
    queue-service = {
      port          = 8082
      health_path   = "/actuator/health"
      cpu           = 512
      memory        = 1024
      desired_count = 2
    }
    notification-service = {
      port          = 8084
      health_path   = "/actuator/health"
      cpu           = 512
      memory        = 1024
      desired_count = 2
    }
  }
}

variable "ai_services" {
  description = "AI Domain(FastAPI) 서비스 — 이름, 컨테이너 포트, health check 경로"
  type = map(object({
    port          = number
    health_path   = string
    cpu           = number
    memory        = number
    desired_count = number
  }))
  default = {
    bot-detection-service = {
      port          = 8091
      health_path   = "/health"
      cpu           = 512
      memory        = 1024
      desired_count = 2
    }
    resale-monitor-service = {
      port          = 8092
      health_path   = "/health"
      cpu           = 512
      memory        = 1024
      desired_count = 2
    }
    # YOLOv8 얼굴 인식 추론 때문에 다른 서비스보다 더 많은 CPU/메모리를 할당한다
    # (k8s/verification-service.yaml과 동일한 근거).
    verification-service = {
      port          = 8093
      health_path   = "/health"
      cpu           = 1024
      memory        = 2048
      desired_count = 2
    }
  }
}

variable "db_instance_class" {
  description = "서비스별 RDS 인스턴스 클래스 — 데모/개발용 최소 사양"
  type        = string
  default     = "db.t4g.micro"
}

variable "redis_node_type" {
  description = "ElastiCache Redis 노드 타입"
  type        = string
  default     = "cache.t4g.micro"
}
