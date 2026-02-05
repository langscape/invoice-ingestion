output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "api_url" {
  value = module.container_app.api_url
}

output "static_web_app_url" {
  value = module.static_web_app.url
}

output "storage_account_name" {
  value = module.storage.account_name
}

output "database_host" {
  value = module.database.host
}

output "azure_openai_endpoint" {
  value = module.azure_openai.endpoint
}
