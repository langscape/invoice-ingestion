output "connection_string" {
  value     = "postgresql+asyncpg://invoiceadmin:${var.db_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/invoice_ingestion?sslmode=require"
  sensitive = true
}

output "host" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "server_id" {
  value = azurerm_postgresql_flexible_server.main.id
}
