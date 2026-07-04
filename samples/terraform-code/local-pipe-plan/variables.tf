variable "service_name" {
  type        = string
  description = "Service name used to build deterministic sample values."
  default     = "tfexplain-local"

  validation {
    condition     = length(var.service_name) > 0
    error_message = "service_name must not be empty."
  }
}

variable "environment" {
  type        = string
  description = "Environment label for the sample."
  default     = "dev"
}

variable "owner" {
  type        = string
  description = "Owner label for the sample."
  default     = "platform"
}

variable "replicas" {
  type        = number
  description = "Replica count to make plan updates easy to test."
  default     = 2

  validation {
    condition     = var.replicas >= 1
    error_message = "replicas must be at least 1."
  }
}

variable "release_version" {
  type        = string
  description = "Changing this value forces replacement of release_gate."
  default     = "2026.07.05-1"
}
