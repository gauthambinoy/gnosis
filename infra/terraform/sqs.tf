# -----------------------------------------------------------------------------
# SQS Queues — Agent execution, webhooks, notifications
# -----------------------------------------------------------------------------

# --- Dead Letter Queue --------------------------------------------------------

resource "aws_sqs_queue" "agent_execution_dlq" {
  name                      = "${var.project_name}-agent-execution-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days
  kms_master_key_id         = aws_kms_key.main.id

  tags = {
    Name = "${var.project_name}-agent-execution-dlq-${var.environment}"
  }
}

# --- Agent Execution Queue ----------------------------------------------------

resource "aws_sqs_queue" "agent_execution" {
  name                       = "${var.project_name}-agent-execution-${var.environment}"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling
  kms_master_key_id          = aws_kms_key.main.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.agent_execution_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${var.project_name}-agent-execution-${var.environment}"
  }
}

# --- Webhooks Queue -----------------------------------------------------------

resource "aws_sqs_queue" "webhooks" {
  name                       = "${var.project_name}-webhooks-${var.environment}"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20
  kms_master_key_id          = aws_kms_key.main.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.agent_execution_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${var.project_name}-webhooks-${var.environment}"
  }
}

# --- Notifications Queue ------------------------------------------------------

resource "aws_sqs_queue" "notifications" {
  name                       = "${var.project_name}-notifications-${var.environment}"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20
  kms_master_key_id          = aws_kms_key.main.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.agent_execution_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${var.project_name}-notifications-${var.environment}"
  }
}
