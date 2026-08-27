output "db_endpoint" {
  description = "Endpoint do RDS (host:porta) para configurar DATABASE_URL do backend"
  value       = aws_db_instance.postgres.endpoint
}

output "db_address" {
  value = aws_db_instance.postgres.address
}

output "db_name" {
  value = aws_db_instance.postgres.db_name
}

output "db_security_group_id" {
  value = aws_security_group.db.id
}
