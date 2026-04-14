# -----------------------------------------------------------------------------
# SSM Parameter Store — Non-secret configuration
# -----------------------------------------------------------------------------

resource "aws_ssm_parameter" "app_version" {
  name        = "/${var.project_name}/${var.environment}/app/version"
  description = "Application version"
  type        = "String"
  value       = "0.1.0"

  tags = {
    Name = "${var.project_name}-${var.environment}-app-version"
  }

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "log_level" {
  name        = "/${var.project_name}/${var.environment}/app/log_level"
  description = "Application log level"
  type        = "String"
  value       = var.environment == "prod" ? "WARNING" : "DEBUG"

  tags = {
    Name = "${var.project_name}-${var.environment}-log-level"
  }
}

resource "aws_ssm_parameter" "rate_limit" {
  name        = "/${var.project_name}/${var.environment}/app/rate_limit"
  description = "API rate limit (requests per minute)"
  type        = "String"
  value       = var.environment == "prod" ? "100" : "1000"

  tags = {
    Name = "${var.project_name}-${var.environment}-rate-limit"
  }
}

resource "aws_ssm_parameter" "feature_flags" {
  name        = "/${var.project_name}/${var.environment}/feature_flags"
  description = "Feature flags (JSON)"
  type        = "String"
  value = jsonencode({
    enable_agent_v2      = false
    enable_export        = true
    enable_notifications = true
    enable_websockets    = false
    max_upload_size_mb   = 50
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-feature-flags"
  }

  lifecycle {
    ignore_changes = [value]
  }
}
