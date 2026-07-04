variable "environment" {
  type        = string
  description = "Environment name."
  default     = "dev"
}

variable "location" {
  type        = string
  description = "Azure region."
  default     = "eastus"
}

variable "node_count" {
  type    = number
  default = 2
}
