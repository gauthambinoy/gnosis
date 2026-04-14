# -----------------------------------------------------------------------------
# Cognito — User Pool for authentication
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool" "main" {
  count = var.enable_cognito ? 1 : 0

  name = "${var.project_name}-users-${var.environment}"

  # Sign-in configuration
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Email verification
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Gnosis — Verify your email"
    email_message        = "Your verification code is {####}"
  }

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  # MFA (optional TOTP)
  mfa_configuration = "OPTIONAL"
  software_token_mfa_configuration {
    enabled = true
  }

  # Custom attributes
  schema {
    name                = "plan_tier"
    attribute_data_type = "String"
    mutable             = true
    string_attribute_constraints {
      min_length = 1
      max_length = 50
    }
  }

  schema {
    name                = "workspace_id"
    attribute_data_type = "String"
    mutable             = true
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # User attribute updates
  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  tags = {
    Name = "${var.project_name}-users-${var.environment}"
  }
}

# --- User Pool Domain ---------------------------------------------------------

resource "aws_cognito_user_pool_domain" "main" {
  count = var.enable_cognito ? 1 : 0

  domain       = "${var.project_name}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main[0].id
}

# --- App Client (Frontend — PKCE, no secret) ----------------------------------

resource "aws_cognito_user_pool_client" "frontend" {
  count = var.enable_cognito ? 1 : 0

  name         = "${var.project_name}-frontend-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main[0].id

  generate_secret                      = false
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]

  callback_urls = var.domain_name != "" ? [
    "https://${var.domain_name}/auth/callback",
  ] : ["http://localhost:3000/auth/callback"]

  logout_urls = var.domain_name != "" ? [
    "https://${var.domain_name}",
  ] : ["http://localhost:3000"]

  prevent_user_existence_errors = "ENABLED"

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
}

# --- Google Identity Provider (configure via console or variables) -------------
# Uncomment and provide Google OAuth credentials to enable
# resource "aws_cognito_identity_provider" "google" {
#   count         = var.enable_cognito ? 1 : 0
#   user_pool_id  = aws_cognito_user_pool.main[0].id
#   provider_name = "Google"
#   provider_type = "Google"
#
#   provider_details = {
#     client_id        = var.google_client_id
#     client_secret    = var.google_client_secret
#     authorize_scopes = "email profile openid"
#   }
#
#   attribute_mapping = {
#     email    = "email"
#     username = "sub"
#   }
# }

# --- GitHub Identity Provider -------------------------------------------------
# Uncomment and provide GitHub OAuth credentials to enable
# resource "aws_cognito_identity_provider" "github" {
#   count         = var.enable_cognito ? 1 : 0
#   user_pool_id  = aws_cognito_user_pool.main[0].id
#   provider_name = "GitHub"
#   provider_type = "OIDC"
#
#   provider_details = {
#     client_id                = var.github_client_id
#     client_secret            = var.github_client_secret
#     authorize_scopes         = "openid user:email"
#     oidc_issuer              = "https://token.actions.githubusercontent.com"
#     attributes_request_method = "GET"
#   }
#
#   attribute_mapping = {
#     email    = "email"
#     username = "sub"
#   }
# }
