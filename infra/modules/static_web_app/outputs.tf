output "url" {
  value = "https://${azurerm_static_web_app.main.default_host_name}"
}

output "id" {
  value = azurerm_static_web_app.main.id
}

output "api_key" {
  value     = azurerm_static_web_app.main.api_key
  sensitive = true
}
