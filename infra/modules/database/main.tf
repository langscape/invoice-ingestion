resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.prefix}-${var.environment}-pgflex"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = "16"
  administrator_login    = "invoiceadmin"
  administrator_password = var.db_admin_password

  storage_mb = 32768
  sku_name   = var.environment == "prod" ? "GP_Standard_D2ds_v5" : "B_Standard_B1ms"

  zone = "1"

  tags = {
    environment = var.environment
    project     = "invoice-ingestion"
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "invoice_ingestion"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
