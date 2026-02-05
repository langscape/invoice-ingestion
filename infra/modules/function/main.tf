resource "azurerm_service_plan" "main" {
  name                = "${var.prefix}-${var.environment}-funcplan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_storage_account" "func" {
  name                     = "${var.prefix}${var.environment}func"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_linux_function_app" "main" {
  name                       = "${var.prefix}-${var.environment}-func"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.func.name
  storage_account_access_key = azurerm_storage_account.func.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "AzureWebJobsStorage"         = var.storage_connection_string
    "FUNCTIONS_WORKER_RUNTIME"    = "python"
    "API_WEBHOOK_URL"             = "${var.api_url}/webhook/blob-trigger"
  }

  tags = {
    environment = var.environment
    project     = "invoice-ingestion"
  }
}
