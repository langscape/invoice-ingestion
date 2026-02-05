terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = "${var.prefix}-${var.environment}-rg"
  location = var.location

  tags = {
    environment = var.environment
    project     = "invoice-ingestion"
  }
}

module "storage" {
  source              = "./modules/storage"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  prefix              = var.prefix
  environment         = var.environment
}

module "database" {
  source              = "./modules/database"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  prefix              = var.prefix
  environment         = var.environment
  db_admin_password   = var.db_admin_password
}

module "azure_openai" {
  source              = "./modules/azure_openai"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  prefix              = var.prefix
  environment         = var.environment
}

module "keyvault" {
  source               = "./modules/keyvault"
  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  prefix               = var.prefix
  environment          = var.environment
  azure_ai_api_key     = var.azure_ai_api_key
  azure_openai_api_key = module.azure_openai.api_key
  db_connection_string = module.database.connection_string
}

module "container_app" {
  source                = "./modules/container_app"
  resource_group_name   = azurerm_resource_group.main.name
  location              = azurerm_resource_group.main.location
  prefix                = var.prefix
  environment           = var.environment
  database_url          = module.database.connection_string
  blob_connection_string = module.storage.connection_string
  keyvault_uri          = module.keyvault.vault_uri
  azure_ai_endpoint     = var.azure_ai_endpoint
  azure_ai_api_key      = var.azure_ai_api_key
  azure_openai_endpoint = module.azure_openai.endpoint
  azure_openai_api_key  = module.azure_openai.api_key
}

module "function" {
  source                    = "./modules/function"
  resource_group_name       = azurerm_resource_group.main.name
  location                  = azurerm_resource_group.main.location
  prefix                    = var.prefix
  environment               = var.environment
  storage_connection_string = module.storage.connection_string
  api_url                   = module.container_app.api_url
}

module "static_web_app" {
  source              = "./modules/static_web_app"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  prefix              = var.prefix
  environment         = var.environment
}
