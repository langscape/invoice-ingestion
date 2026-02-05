resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.prefix}-${var.environment}-logs"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "main" {
  name                       = "${var.prefix}-${var.environment}-env"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_container_app" "api" {
  name                         = "${var.prefix}-${var.environment}-api"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  template {
    min_replicas = var.environment == "prod" ? 1 : 0
    max_replicas = var.environment == "prod" ? 5 : 2

    container {
      name   = "api"
      image  = "ghcr.io/invoice-ingestion/api:latest"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "INVOICE_DATABASE_URL"
        value = var.database_url
      }

      env {
        name  = "INVOICE_BLOB_CONNECTION_STRING"
        value = var.blob_connection_string
      }

      env {
        name  = "INVOICE_AZURE_AI_ENDPOINT"
        value = var.azure_ai_endpoint
      }

      env {
        name        = "INVOICE_AZURE_AI_API_KEY"
        secret_name = "azure-ai-api-key"
      }

      env {
        name  = "INVOICE_AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }

      env {
        name        = "INVOICE_AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }

      env {
        name  = "INVOICE_API_HOST"
        value = "0.0.0.0"
      }

      env {
        name  = "INVOICE_API_PORT"
        value = "8000"
      }
    }
  }

  secret {
    name  = "azure-ai-api-key"
    value = var.azure_ai_api_key
  }

  secret {
    name  = "azure-openai-api-key"
    value = var.azure_openai_api_key
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

resource "azurerm_container_app" "worker" {
  name                         = "${var.prefix}-${var.environment}-worker"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "worker"
      image  = "ghcr.io/invoice-ingestion/worker:latest"
      cpu    = 2.0
      memory = "4Gi"

      command = ["python", "-m", "invoice_ingestion.workers.blob_processor"]

      env {
        name  = "INVOICE_DATABASE_URL"
        value = var.database_url
      }

      env {
        name  = "INVOICE_BLOB_CONNECTION_STRING"
        value = var.blob_connection_string
      }

      env {
        name  = "INVOICE_AZURE_AI_ENDPOINT"
        value = var.azure_ai_endpoint
      }

      env {
        name        = "INVOICE_AZURE_AI_API_KEY"
        secret_name = "azure-ai-api-key"
      }

      env {
        name  = "INVOICE_AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }

      env {
        name        = "INVOICE_AZURE_OPENAI_API_KEY"
        secret_name = "azure-openai-api-key"
      }
    }
  }

  secret {
    name  = "azure-ai-api-key"
    value = var.azure_ai_api_key
  }

  secret {
    name  = "azure-openai-api-key"
    value = var.azure_openai_api_key
  }
}
