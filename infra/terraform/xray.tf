# -----------------------------------------------------------------------------
# X-Ray — Distributed tracing
# -----------------------------------------------------------------------------

resource "aws_xray_sampling_rule" "main" {
  count = var.enable_xray ? 1 : 0

  rule_name      = "${var.project_name}-${var.environment}"
  priority       = 1000
  version        = 1
  reservoir_size = 1
  fixed_rate     = var.environment == "prod" ? 0.05 : 0.5 # 5% prod, 50% dev
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "${var.project_name}-${var.environment}"
  resource_arn   = "*"

  tags = {
    Name = "${var.project_name}-${var.environment}-xray-sampling"
  }
}

resource "aws_xray_group" "errors" {
  count = var.enable_xray ? 1 : 0

  group_name        = "${var.project_name}-${var.environment}-errors"
  filter_expression = "responsetime > 5 OR error = true OR fault = true"

  tags = {
    Name = "${var.project_name}-${var.environment}-xray-errors"
  }
}

resource "aws_xray_encryption_config" "main" {
  count = var.enable_xray ? 1 : 0

  type   = "KMS"
  key_id = aws_kms_key.main.arn
}
