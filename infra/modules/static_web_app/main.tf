resource "azurerm_static_web_app" "main" {
  name                = "${var.prefix}-${var.environment}-swa"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_tier            = var.environment == "prod" ? "Standard" : "Free"
  sku_size            = var.environment == "prod" ? "Standard" : "Free"

  tags = {
    environment = var.environment
    project     = "invoice-ingestion"
  }
}
