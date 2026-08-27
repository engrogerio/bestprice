terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "opentofu"
  }
}

# ------------------------------------------------------------
# Security Group: só libera 5432 para os CIDRs do backend
# ------------------------------------------------------------
resource "aws_security_group" "db" {
  name        = "${local.name_prefix}-db-sg"
  description = "Acesso ao Postgres do BestPrice"
  vpc_id      = var.vpc_id

  ingress {
    description = "Postgres a partir do backend"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.name_prefix}-db-sg" })
}

# ------------------------------------------------------------
# DB Subnet Group
# ------------------------------------------------------------
resource "aws_db_subnet_group" "this" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = var.subnet_ids
  tags       = local.tags
}

# ------------------------------------------------------------
# Parameter Group (ajustes finos de Postgres, se necessário)
# ------------------------------------------------------------
resource "aws_db_parameter_group" "this" {
  name   = "${local.name_prefix}-pg-params"
  family = "postgres${var.postgres_version}"

  parameter {
    name  = "log_min_duration_statement"
    value = "500" # loga queries > 500ms, útil para achar consultas lentas do histórico de preços
  }

  tags = local.tags
}

# ------------------------------------------------------------
# RDS Postgres
# ------------------------------------------------------------
resource "aws_db_instance" "postgres" {
  identifier     = "${local.name_prefix}-postgres"
  engine         = "postgres"
  engine_version = var.postgres_version

  instance_class        = var.instance_class
  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.allocated_storage_gb * 5 # autoscaling de storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = aws_db_parameter_group.this.name

  multi_az                = var.multi_az
  backup_retention_period = var.backup_retention_days
  backup_window            = "03:00-04:00" # horário de Brasília (UTC-3) ~ madrugada
  maintenance_window       = "sun:04:30-sun:05:30"

  publicly_accessible       = false
  deletion_protection       = var.environment == "prod"
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.name_prefix}-final-snapshot" : null
  auto_minor_version_upgrade = true

  tags = merge(local.tags, { Name = "${local.name_prefix}-postgres" })
}
