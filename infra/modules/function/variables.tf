variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "prefix" { type = string }
variable "environment" { type = string }
variable "storage_connection_string" {
  type      = string
  sensitive = true
}
variable "api_url" { type = string }
