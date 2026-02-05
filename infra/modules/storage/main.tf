resource "azurerm_storage_account" "main" {
  name                     = "${var.prefix}${var.environment}store"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "HEAD"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }

  tags = {
    environment = var.environment
    project     = "invoice-ingestion"
  }
}

resource "azurerm_storage_container" "imported" {
  name                  = "imported"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "extracted" {
  name                  = "extracted"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}
