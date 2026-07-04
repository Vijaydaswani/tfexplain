variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}

variable "zone_name" {
  type        = string
  description = "Cloudflare zone name."
}

variable "record_name" {
  type        = string
  description = "DNS record name."
  default     = "app"
}

variable "record_value" {
  type        = string
  description = "DNS target."
}
