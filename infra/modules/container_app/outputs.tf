output "api_url" {
  value = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "api_id" {
  value = azurerm_container_app.api.id
}
