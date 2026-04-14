# -----------------------------------------------------------------------------
# SES — Simple Email Service for notifications
# -----------------------------------------------------------------------------

resource "aws_ses_email_identity" "notifications" {
  email = var.alert_email
}

resource "aws_ses_configuration_set" "main" {
  name = "${var.project_name}-${var.environment}"

  delivery_options {
    tls_policy = "Require"
  }
}

resource "aws_ses_event_destination" "cloudwatch" {
  name                   = "${var.project_name}-${var.environment}-cloudwatch"
  configuration_set_name = aws_ses_configuration_set.main.name
  enabled                = true

  matching_types = [
    "bounce",
    "complaint",
    "delivery",
    "reject",
    "send",
  ]

  cloudwatch_destination {
    default_value  = "default"
    dimension_name = "ses:source-ip"
    value_source   = "messageTag"
  }
}

# IAM policy allowing ECS tasks to send emails via SES
resource "aws_iam_policy" "ses_send" {
  name        = "${var.project_name}-${var.environment}-ses-send"
  description = "Allow sending emails via SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ses:SendEmail",
        "ses:SendRawEmail",
        "ses:SendTemplatedEmail",
      ]
      Resource = "*"
      Condition = {
        StringEquals = {
          "ses:FromAddress" = var.alert_email
        }
      }
    }]
  })
}
