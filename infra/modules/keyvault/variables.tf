variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "prefix" { type = string }
variable "environment" { type = string }
variable "azure_ai_api_key" {
  type      = string
  sensitive = true
}
variable "azure_openai_api_key" {
  type      = string
  sensitive = true
}
variable "db_connection_string" {
  type      = string
  sensitive = true
}
