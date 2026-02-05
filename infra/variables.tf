variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "invoiceai"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus2"
}

variable "db_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "azure_ai_endpoint" {
  description = "Azure AI Foundry endpoint for Claude model deployments"
  type        = string
}

variable "azure_ai_api_key" {
  description = "Azure AI Foundry API key for Claude models"
  type        = string
  sensitive   = true
}
