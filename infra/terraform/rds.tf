# -----------------------------------------------------------------------------
# RDS Subnet Group
# -----------------------------------------------------------------------------
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${var.project_name}-${var.environment}-db-subnet-group" }
}

# -----------------------------------------------------------------------------
# RDS PostgreSQL 16
# -----------------------------------------------------------------------------
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-${var.environment}-postgres"
  engine         = "postgres"
  engine_version = "16"

  instance_class        = var.db_instance_class
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = false # Set to true for production
  publicly_accessible = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  # Set to true for production to prevent accidental deletion
  deletion_protection = false
  skip_final_snapshot = true

  performance_insights_enabled = false

  tags = { Name = "${var.project_name}-${var.environment}-postgres" }

  lifecycle {
    prevent_destroy = false # Set to true for production
  }
}
