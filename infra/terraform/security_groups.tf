# -----------------------------------------------------------------------------
# ALB Security Group — accepts HTTP/HTTPS from the internet
# -----------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-${var.environment}-alb-"
  description = "Allow inbound HTTP/HTTPS from the internet"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project_name}-${var.environment}-alb-sg" }

  lifecycle { create_before_destroy = true }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from internet"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from internet"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_all_out" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow all outbound"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# -----------------------------------------------------------------------------
# ECS Security Group — accepts traffic only from ALB
# -----------------------------------------------------------------------------
resource "aws_security_group" "ecs" {
  name_prefix = "${var.project_name}-${var.environment}-ecs-"
  description = "Allow inbound from ALB only"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project_name}-${var.environment}-ecs-sg" }

  lifecycle { create_before_destroy = true }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb_backend" {
  security_group_id            = aws_security_group.ecs.id
  description                  = "Backend traffic from ALB"
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb_frontend" {
  security_group_id            = aws_security_group.ecs.id
  description                  = "Frontend traffic from ALB"
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 3000
  to_port                      = 3000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "ecs_all_out" {
  security_group_id = aws_security_group.ecs.id
  description       = "Allow all outbound (ECR pulls, Secrets Manager, etc.)"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# -----------------------------------------------------------------------------
# RDS Security Group — accepts traffic only from ECS
# -----------------------------------------------------------------------------
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  description = "Allow PostgreSQL from ECS tasks only"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project_name}-${var.environment}-rds-sg" }

  lifecycle { create_before_destroy = true }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  security_group_id            = aws_security_group.rds.id
  description                  = "PostgreSQL from ECS"
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "rds_all_out" {
  security_group_id = aws_security_group.rds.id
  description       = "Allow all outbound"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# -----------------------------------------------------------------------------
# Redis Security Group — accepts traffic only from ECS
# -----------------------------------------------------------------------------
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-${var.environment}-redis-"
  description = "Allow Redis from ECS tasks only"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project_name}-${var.environment}-redis-sg" }

  lifecycle { create_before_destroy = true }
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_ecs" {
  security_group_id            = aws_security_group.redis.id
  description                  = "Redis from ECS"
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "redis_all_out" {
  security_group_id = aws_security_group.redis.id
  description       = "Allow all outbound"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
