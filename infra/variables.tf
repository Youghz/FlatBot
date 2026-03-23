variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "sandbox-hugo"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "northamerica-northeast1"
}

variable "telegram_bot_token" {
  description = "Telegram bot API token"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Cloud SQL postgres password"
  type        = string
  sensitive   = true
  default     = ""  # Auto-generated if empty
}

variable "jwt_secret_key" {
  description = "JWT signing key"
  type        = string
  sensitive   = true
  default     = ""  # Auto-generated if empty
}
