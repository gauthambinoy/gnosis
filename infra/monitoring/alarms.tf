###############################################################################
# SNS Topic for alarm notifications
###############################################################################

resource "aws_sns_topic" "gnosis_alarms" {
  name = "gnosis-alarms"
}

variable "alarm_email" {
  description = "Email address for alarm notifications"
  type        = string
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.gnosis_alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

###############################################################################
# ECS — High CPU Utilization (>80%)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "ecs_backend_high_cpu" {
  alarm_name          = "gnosis-ecs-backend-high-cpu"
  alarm_description   = "Backend ECS service CPU utilization exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = "gnosis-cluster"
    ServiceName = "gnosis-backend"
  }

  alarm_actions = [aws_sns_topic.gnosis_alarms.arn]
  ok_actions    = [aws_sns_topic.gnosis_alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "ecs_frontend_high_cpu" {
  alarm_name          = "gnosis-ecs-frontend-high-cpu"
  alarm_description   = "Frontend ECS service CPU utilization exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = "gnosis-cluster"
    ServiceName = "gnosis-frontend"
  }

  alarm_actions = [aws_sns_topic.gnosis_alarms.arn]
  ok_actions    = [aws_sns_topic.gnosis_alarms.arn]
}

###############################################################################
# ALB — High 5xx Error Rate (>10 in 5 min)
###############################################################################

variable "alb_arn_suffix" {
  description = "ARN suffix of the ALB (e.g. app/gnosis-alb/0123456789)"
  type        = string
}

resource "aws_cloudwatch_metric_alarm" "alb_high_5xx" {
  alarm_name          = "gnosis-alb-high-5xx"
  alarm_description   = "ALB 5xx errors exceed 10 in 5 minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.gnosis_alarms.arn]
  ok_actions    = [aws_sns_topic.gnosis_alarms.arn]
}

###############################################################################
# ALB — High Latency (p99 > 2s)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "alb_high_latency" {
  alarm_name          = "gnosis-alb-high-latency"
  alarm_description   = "ALB p99 target response time exceeds 2 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 2

  metric_query {
    id          = "latency_p99"
    return_data = true

    metric {
      metric_name = "TargetResponseTime"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "p99"

      dimensions = {
        LoadBalancer = var.alb_arn_suffix
      }
    }
  }

  treat_missing_data = "notBreaching"
  alarm_actions      = [aws_sns_topic.gnosis_alarms.arn]
  ok_actions         = [aws_sns_topic.gnosis_alarms.arn]
}

###############################################################################
# RDS — Low Free Storage (<20% of allocated)
###############################################################################

variable "rds_instance_id" {
  description = "RDS instance identifier"
  type        = string
  default     = "gnosis-db"
}

variable "rds_allocated_storage_bytes" {
  description = "Total allocated RDS storage in bytes"
  type        = number
  default     = 21474836480 # 20 GiB
}

resource "aws_cloudwatch_metric_alarm" "rds_low_storage" {
  alarm_name          = "gnosis-rds-low-storage"
  alarm_description   = "RDS free storage space is below 20% of allocated storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.rds_allocated_storage_bytes * 0.2
  treat_missing_data  = "breaching"

  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }

  alarm_actions = [aws_sns_topic.gnosis_alarms.arn]
  ok_actions    = [aws_sns_topic.gnosis_alarms.arn]
}

###############################################################################
# RDS — High CPU (>80%)
###############################################################################

resource "aws_cloudwatch_metric_alarm" "rds_high_cpu" {
  alarm_name          = "gnosis-rds-high-cpu"
  alarm_description   = "RDS CPU utilization exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = var.rds_instance_id
  }

  alarm_actions = [aws_sns_topic.gnosis_alarms.arn]
  ok_actions    = [aws_sns_topic.gnosis_alarms.arn]
}

###############################################################################
# Redis — High Memory Usage (>80%)
###############################################################################

variable "redis_cluster_id" {
  description = "ElastiCache Redis cluster identifier"
  type        = string
  default     = "gnosis-redis"
}

resource "aws_cloudwatch_metric_alarm" "redis_high_memory" {
  alarm_name          = "gnosis-redis-high-memory"
  alarm_description   = "Redis memory usage exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "notBreaching"

  dimensions = {
    CacheClusterId = var.redis_cluster_id
  }

  alarm_actions = [aws_sns_topic.gnosis_alarms.arn]
  ok_actions    = [aws_sns_topic.gnosis_alarms.arn]
}
