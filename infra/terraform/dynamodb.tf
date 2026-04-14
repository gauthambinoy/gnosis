# -----------------------------------------------------------------------------
# DynamoDB — Execution history, sessions, rate limits
# -----------------------------------------------------------------------------

# --- Execution History --------------------------------------------------------

resource "aws_dynamodb_table" "execution_history" {
  name         = "${var.project_name}-execution-history-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "agent_id"
  range_key    = "timestamp"

  attribute {
    name = "agent_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user-id-index"
    hash_key        = "user_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-execution-history-${var.environment}"
  }
}

# --- Sessions -----------------------------------------------------------------

resource "aws_dynamodb_table" "sessions" {
  name         = "${var.project_name}-sessions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  tags = {
    Name = "${var.project_name}-sessions-${var.environment}"
  }
}

# --- Rate Limits --------------------------------------------------------------

resource "aws_dynamodb_table" "rate_limits" {
  name         = "${var.project_name}-rate-limits-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "key"

  attribute {
    name = "key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  tags = {
    Name = "${var.project_name}-rate-limits-${var.environment}"
  }
}
