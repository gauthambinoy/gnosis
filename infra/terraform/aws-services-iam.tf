# -----------------------------------------------------------------------------
# IAM Policy — ECS task access to all AWS services
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "ecs_aws_services" {
  # S3 access
  statement {
    sid    = "S3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.uploads.arn,
      "${aws_s3_bucket.uploads.arn}/*",
      aws_s3_bucket.exports.arn,
      "${aws_s3_bucket.exports.arn}/*",
      aws_s3_bucket.backups.arn,
      "${aws_s3_bucket.backups.arn}/*",
    ]
  }

  # SQS access
  statement {
    sid    = "SQSAccess"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [
      aws_sqs_queue.agent_execution.arn,
      aws_sqs_queue.agent_execution_dlq.arn,
      aws_sqs_queue.webhooks.arn,
      aws_sqs_queue.notifications.arn,
    ]
  }

  # SES access
  statement {
    sid    = "SESAccess"
    effect = "Allow"
    actions = [
      "ses:SendEmail",
      "ses:SendRawEmail",
      "ses:SendTemplatedEmail",
    ]
    resources = ["*"]
  }

  # DynamoDB access
  statement {
    sid    = "DynamoDBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [
      aws_dynamodb_table.execution_history.arn,
      "${aws_dynamodb_table.execution_history.arn}/index/*",
      aws_dynamodb_table.sessions.arn,
      aws_dynamodb_table.rate_limits.arn,
    ]
  }

  # SSM Parameter Store access
  statement {
    sid    = "SSMAccess"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = [
      "arn:aws:ssm:${var.region}:${local.account_id}:parameter/${var.project_name}/${var.environment}/*",
    ]
  }

  # SNS access
  statement {
    sid    = "SNSAccess"
    effect = "Allow"
    actions = [
      "sns:Publish",
    ]
    resources = [
      aws_sns_topic.alarms.arn,
      aws_sns_topic.deployment.arn,
      aws_sns_topic.user_events.arn,
    ]
  }

  # X-Ray access
  statement {
    sid    = "XRayAccess"
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
      "xray:GetSamplingStatisticSummaries",
    ]
    resources = ["*"]
  }

  # KMS access
  statement {
    sid    = "KMSAccess"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:GenerateDataKey*",
    ]
    resources = [aws_kms_key.main.arn]
  }
}

resource "aws_iam_policy" "ecs_aws_services" {
  name        = "${var.project_name}-${var.environment}-ecs-aws-services"
  description = "Grant ECS tasks access to S3, SQS, SES, DynamoDB, SSM, SNS, X-Ray, KMS"
  policy      = data.aws_iam_policy_document.ecs_aws_services.json

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-aws-services"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_aws_services" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_aws_services.arn
}
