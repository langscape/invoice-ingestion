variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "prefix" { type = string }
variable "environment" { type = string }
variable "db_admin_password" {
  type      = string
  sensitive = true
}
