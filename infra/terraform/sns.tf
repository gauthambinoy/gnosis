# -----------------------------------------------------------------------------
# SNS Topics — Alarms, deployments, user events
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "alarms" {
  name              = "${var.project_name}-alarms-${var.environment}"
  kms_master_key_id = aws_kms_key.main.id

  tags = {
    Name = "${var.project_name}-alarms-${var.environment}"
  }
}

resource "aws_sns_topic" "deployment" {
  name              = "${var.project_name}-deployment-${var.environment}"
  kms_master_key_id = aws_kms_key.main.id

  tags = {
    Name = "${var.project_name}-deployment-${var.environment}"
  }
}

resource "aws_sns_topic" "user_events" {
  name              = "${var.project_name}-user-events-${var.environment}"
  kms_master_key_id = aws_kms_key.main.id

  tags = {
    Name = "${var.project_name}-user-events-${var.environment}"
  }
}

# --- Email subscription for alarms -------------------------------------------

resource "aws_sns_topic_subscription" "alarms_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# --- SNS Topic Policies (allow CloudWatch Alarms to publish) ------------------

resource "aws_sns_topic_policy" "alarms" {
  arn = aws_sns_topic.alarms.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchAlarms"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.alarms.arn
      },
      {
        Sid    = "AllowAccountPublish"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.account_id}:root"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.alarms.arn
      },
    ]
  })
}
