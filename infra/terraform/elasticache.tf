# -----------------------------------------------------------------------------
# ElastiCache Subnet Group
# -----------------------------------------------------------------------------
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${var.project_name}-${var.environment}-redis-subnet-group" }
}

# -----------------------------------------------------------------------------
# ElastiCache Redis 7
# -----------------------------------------------------------------------------
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.project_name}-${var.environment}-redis"
  description          = "${var.project_name} ${var.environment} Redis cluster"

  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.redis_node_type
  num_cache_clusters   = 1 # Increase for production HA
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = false # Set true if clients support TLS

  automatic_failover_enabled = false # Requires num_cache_clusters >= 2

  snapshot_retention_limit = 3
  snapshot_window          = "02:00-03:00"
  maintenance_window       = "mon:03:00-mon:04:00"

  tags = { Name = "${var.project_name}-${var.environment}-redis" }

  lifecycle {
    prevent_destroy = false # Set to true for production
  }
}
