variable "aws_region" {
  description = "Região AWS onde o RDS será criado"
  type        = string
  default     = "sa-east-1" # São Paulo
}

variable "project_name" {
  description = "Prefixo usado para nomear os recursos"
  type        = string
  default     = "bestprice"
}

variable "environment" {
  description = "dev | staging | prod"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "VPC onde o RDS e o security group serão criados"
  type        = string
}

variable "subnet_ids" {
  description = "Lista de subnets (privadas, de preferência) para o DB Subnet Group"
  type        = list(string)
}

variable "allowed_cidr_blocks" {
  description = "CIDRs autorizados a acessar o Postgres na porta 5432 (ex: VPC do backend/ECS)"
  type        = list(string)
}

variable "db_name" {
  description = "Nome do banco de dados inicial"
  type        = string
  default     = "bestprice"
}

variable "db_username" {
  description = "Usuário master do RDS"
  type        = string
  default     = "bestprice_admin"
}

variable "db_password" {
  description = "Senha master do RDS (recomendado: passar via TF_VAR_db_password ou usar aws_db_instance com manage_master_user_password = true)"
  type        = string
  sensitive   = true
}

variable "instance_class" {
  description = "Classe da instância RDS"
  type        = string
  default     = "db.t4g.micro" # suficiente para dev/MVP; subir para t4g.small/medium em prod
}

variable "allocated_storage_gb" {
  description = "Armazenamento inicial em GB"
  type        = number
  default     = 20
}

variable "multi_az" {
  description = "Ativar Multi-AZ (recomendado em produção)"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Dias de retenção de backup automático"
  type        = number
  default     = 7
}

variable "postgres_version" {
  description = "Versão major do Postgres"
  type        = string
  default     = "16"
}
