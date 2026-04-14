# -----------------------------------------------------------------------------
# Route 53 — DNS (optional, uncomment when domain is available)
# -----------------------------------------------------------------------------

# Uncomment the resources below and provide your domain name via the
# domain_name variable to enable DNS management.

# resource "aws_route53_zone" "main" {
#   count = var.domain_name != "" ? 1 : 0
#   name  = var.domain_name
#
#   tags = {
#     Name = "${var.project_name}-${var.environment}-zone"
#   }
# }

# --- A Record pointing to CloudFront ------------------------------------------
# resource "aws_route53_record" "a" {
#   count   = var.domain_name != "" ? 1 : 0
#   zone_id = aws_route53_zone.main[0].zone_id
#   name    = var.domain_name
#   type    = "A"
#
#   alias {
#     name                   = aws_cloudfront_distribution.main[0].domain_name
#     zone_id                = aws_cloudfront_distribution.main[0].hosted_zone_id
#     evaluate_target_health = false
#   }
# }

# --- AAAA Record for IPv6 -----------------------------------------------------
# resource "aws_route53_record" "aaaa" {
#   count   = var.domain_name != "" ? 1 : 0
#   zone_id = aws_route53_zone.main[0].zone_id
#   name    = var.domain_name
#   type    = "AAAA"
#
#   alias {
#     name                   = aws_cloudfront_distribution.main[0].domain_name
#     zone_id                = aws_cloudfront_distribution.main[0].hosted_zone_id
#     evaluate_target_health = false
#   }
# }

# --- Health Check for backend -------------------------------------------------
# resource "aws_route53_health_check" "backend" {
#   count             = var.domain_name != "" ? 1 : 0
#   fqdn              = var.domain_name
#   port              = 443
#   type              = "HTTPS"
#   resource_path     = "/api/health"
#   failure_threshold = 3
#   request_interval  = 30
#
#   tags = {
#     Name = "${var.project_name}-${var.environment}-health-check"
#   }
# }
