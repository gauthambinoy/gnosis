# -----------------------------------------------------------------------------
# Secrets Manager — stores sensitive configuration consumed by ECS tasks
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.project_name}/${var.environment}/DATABASE_URL"
  description             = "PostgreSQL connection string"
  recovery_window_in_days = 7

  tags = { Name = "${var.project_name}-${var.environment}-database-url" }
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}/${var.db_name}"
}

resource "aws_secretsmanager_secret" "redis_url" {
  name                    = "${var.project_name}/${var.environment}/REDIS_URL"
  description             = "Redis connection string"
  recovery_window_in_days = 7

  tags = { Name = "${var.project_name}-${var.environment}-redis-url" }
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  secret_id     = aws_secretsmanager_secret.redis_url.id
  secret_string = "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0"
}

resource "aws_secretsmanager_secret" "secret_key" {
  name                    = "${var.project_name}/${var.environment}/SECRET_KEY"
  description             = "Application secret key"
  recovery_window_in_days = 7

  tags = { Name = "${var.project_name}-${var.environment}-secret-key" }
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id     = aws_secretsmanager_secret.secret_key.id
  secret_string = random_password.secret_key.result
}

resource "aws_secretsmanager_secret" "openrouter_api_key" {
  name                    = "${var.project_name}/${var.environment}/OPENROUTER_API_KEY"
  description             = "OpenRouter API key"
  recovery_window_in_days = 7

  tags = { Name = "${var.project_name}-${var.environment}-openrouter-api-key" }
}

resource "aws_secretsmanager_secret_version" "openrouter_api_key" {
  secret_id     = aws_secretsmanager_secret.openrouter_api_key.id
  secret_string = var.openrouter_api_key != "" ? var.openrouter_api_key : "PLACEHOLDER_CHANGE_ME"
}
