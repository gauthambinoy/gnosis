# -----------------------------------------------------------------------------
# General
# -----------------------------------------------------------------------------
variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "gnosis"
}

# -----------------------------------------------------------------------------
# Database (RDS)
# -----------------------------------------------------------------------------
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "gnosis"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "gnosis_admin"
}

# -----------------------------------------------------------------------------
# Redis (ElastiCache)
# -----------------------------------------------------------------------------
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# -----------------------------------------------------------------------------
# ECS — Backend
# -----------------------------------------------------------------------------
variable "backend_cpu" {
  description = "CPU units for backend ECS task (1 vCPU = 1024)"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Memory (MiB) for backend ECS task"
  type        = number
  default     = 1024
}

# -----------------------------------------------------------------------------
# ECS — Frontend
# -----------------------------------------------------------------------------
variable "frontend_cpu" {
  description = "CPU units for frontend ECS task"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Memory (MiB) for frontend ECS task"
  type        = number
  default     = 512
}

# -----------------------------------------------------------------------------
# Networking / Domain
# -----------------------------------------------------------------------------
variable "domain_name" {
  description = "Domain name for the application (e.g. gnosis.example.com). Leave empty to skip ACM/CloudFront custom domain."
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Application Secrets
# -----------------------------------------------------------------------------
variable "openrouter_api_key" {
  description = "OpenRouter API key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

# -----------------------------------------------------------------------------
# Alerts / Notifications
# -----------------------------------------------------------------------------
variable "alert_email" {
  description = "Email address for SNS alarm notifications and SES sender identity"
  type        = string
  default     = "alerts@example.com"
}

# -----------------------------------------------------------------------------
# Feature Toggles
# -----------------------------------------------------------------------------
variable "enable_waf" {
  description = "Enable WAF v2 Web ACL on the ALB"
  type        = bool
  default     = true
}

variable "enable_cognito" {
  description = "Enable Cognito User Pool for authentication"
  type        = bool
  default     = true
}

variable "enable_xray" {
  description = "Enable X-Ray distributed tracing"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Backup / Lifecycle
# -----------------------------------------------------------------------------
variable "backup_retention_days" {
  description = "Number of days to retain RDS backups"
  type        = number
  default     = 7
}

variable "s3_lifecycle_days" {
  description = "Number of days before S3 upload objects expire"
  type        = number
  default     = 90
}
