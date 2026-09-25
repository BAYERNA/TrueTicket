resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-redis"
  subnet_ids = [for s in aws_subnet.private : s.id]
}

# gateway-service(rate limiting)와 queue-service(가상대기열 Sorted Set)가 공유한다 —
# docker-compose.yml의 단일 redis 컨테이너와 동일한 구성.
resource "aws_elasticache_cluster" "main" {
  cluster_id         = "${local.name_prefix}-redis"
  engine             = "redis"
  engine_version     = "7.1"
  node_type          = var.redis_node_type
  num_cache_nodes    = 1
  port               = 6379
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  tags = { Name = "${local.name_prefix}-redis" }
}
