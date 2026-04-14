# -----------------------------------------------------------------------------
# Lambda Functions — Webhook processor, cleanup, DB backup
# -----------------------------------------------------------------------------

# --- IAM Role for Lambda ------------------------------------------------------

resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-${var.environment}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-exec"
  }
}

resource "aws_iam_role_policy" "lambda_base" {
  name = "${var.project_name}-${var.environment}-lambda-base"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.region}:${local.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
        ]
        Resource = [
          aws_sqs_queue.webhooks.arn,
          aws_sqs_queue.agent_execution.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
        ]
        Resource = [
          aws_dynamodb_table.execution_history.arn,
          "${aws_dynamodb_table.execution_history.arn}/index/*",
          aws_dynamodb_table.sessions.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
        ]
        Resource = aws_kms_key.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "rds:CreateDBSnapshot",
          "rds:DescribeDBInstances",
          "rds:DescribeDBSnapshots",
          "rds:DeleteDBSnapshot",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
        ]
        Resource = "${aws_s3_bucket.backups.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
        ]
        Resource = "*"
      },
    ]
  })
}

# --- Webhook Processor Lambda -------------------------------------------------

data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/lambda_placeholder.zip"

  source {
    content  = <<-PYTHON
      import json
      import logging

      logger = logging.getLogger()
      logger.setLevel(logging.INFO)

      def handler(event, context):
          """Placeholder Lambda handler — replace with actual implementation."""
          logger.info("Received event: %s", json.dumps(event))
          for record in event.get("Records", []):
              logger.info("Processing message: %s", record.get("messageId"))
          return {"statusCode": 200, "body": "OK"}
    PYTHON
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "webhook_processor" {
  function_name = "${var.project_name}-webhook-processor-${var.environment}"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "lambda_function.handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 128

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      ENVIRONMENT  = var.environment
      PROJECT_NAME = var.project_name
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = {
    Name = "${var.project_name}-webhook-processor-${var.environment}"
  }
}

resource "aws_lambda_event_source_mapping" "webhook_sqs" {
  event_source_arn = aws_sqs_queue.webhooks.arn
  function_name    = aws_lambda_function.webhook_processor.arn
  batch_size       = 10
  enabled          = true
}

# --- Cleanup Lambda (daily) ---------------------------------------------------

resource "aws_lambda_function" "cleanup" {
  function_name = "${var.project_name}-cleanup-${var.environment}"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "lambda_function.handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 128

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      PROJECT_NAME       = var.project_name
      SESSIONS_TABLE     = aws_dynamodb_table.sessions.name
      RATE_LIMITS_TABLE  = aws_dynamodb_table.rate_limits.name
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = {
    Name = "${var.project_name}-cleanup-${var.environment}"
  }
}

resource "aws_cloudwatch_event_rule" "daily_cleanup" {
  name                = "${var.project_name}-daily-cleanup-${var.environment}"
  description         = "Trigger daily cleanup of expired sessions and cache"
  schedule_expression = "rate(1 day)"

  tags = {
    Name = "${var.project_name}-daily-cleanup-${var.environment}"
  }
}

resource "aws_cloudwatch_event_target" "cleanup" {
  rule = aws_cloudwatch_event_rule.daily_cleanup.name
  arn  = aws_lambda_function.cleanup.arn
}

resource "aws_lambda_permission" "cleanup_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cleanup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_cleanup.arn
}

# --- DB Backup Lambda (weekly) ------------------------------------------------

resource "aws_lambda_function" "db_backup" {
  function_name = "${var.project_name}-db-backup-${var.environment}"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "lambda_function.handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 128

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      PROJECT_NAME       = var.project_name
      RDS_INSTANCE_ID    = aws_db_instance.main.identifier
      BACKUP_BUCKET      = aws_s3_bucket.backups.id
      RETENTION_DAYS     = tostring(var.backup_retention_days)
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = {
    Name = "${var.project_name}-db-backup-${var.environment}"
  }
}

resource "aws_cloudwatch_event_rule" "weekly_backup" {
  name                = "${var.project_name}-weekly-backup-${var.environment}"
  description         = "Trigger weekly RDS snapshot"
  schedule_expression = "rate(7 days)"

  tags = {
    Name = "${var.project_name}-weekly-backup-${var.environment}"
  }
}

resource "aws_cloudwatch_event_target" "db_backup" {
  rule = aws_cloudwatch_event_rule.weekly_backup.name
  arn  = aws_lambda_function.db_backup.arn
}

resource "aws_lambda_permission" "db_backup_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.db_backup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_backup.arn
}

# --- CloudWatch Log Groups for Lambda -----------------------------------------

resource "aws_cloudwatch_log_group" "webhook_processor" {
  name              = "/aws/lambda/${aws_lambda_function.webhook_processor.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-webhook-processor-logs-${var.environment}"
  }
}

resource "aws_cloudwatch_log_group" "cleanup" {
  name              = "/aws/lambda/${aws_lambda_function.cleanup.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-cleanup-logs-${var.environment}"
  }
}

resource "aws_cloudwatch_log_group" "db_backup" {
  name              = "/aws/lambda/${aws_lambda_function.db_backup.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-db-backup-logs-${var.environment}"
  }
}
