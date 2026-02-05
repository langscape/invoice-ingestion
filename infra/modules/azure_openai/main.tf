resource "azurerm_cognitive_account" "openai" {
  name                = "${var.prefix}-${var.environment}-openai"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name = "${var.prefix}-${var.environment}-openai"

  tags = {
    environment = var.environment
    project     = "invoice-ingestion"
  }
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }

  sku {
    name     = "Standard"
    capacity = var.environment == "prod" ? 80 : 30
  }
}

resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }

  sku {
    name     = "Standard"
    capacity = var.environment == "prod" ? 80 : 30
  }
}
