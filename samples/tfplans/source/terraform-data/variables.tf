variable "service_name" {
  type        = string
  description = "Service name represented in the sample plan."
  default     = "tfexplain-sample"

  validation {
    condition     = length(var.service_name) > 0
    error_message = "service_name must not be empty."
  }
}

variable "environment" {
  type        = string
  description = "Environment represented in the sample plan."
  default     = "dev"
}

variable "owner" {
  type        = string
  description = "Owner tag for the sample plan."
  default     = "platform"
}

variable "replicas" {
  type        = number
  description = "Replica count used to create update-style plan changes."
  default     = 2

  validation {
    condition     = var.replicas >= 1
    error_message = "replicas must be at least 1."
  }
}

variable "reviewers" {
  type        = list(string)
  description = "Reviewers included in the sample plan input."
  default     = ["platform"]
}

variable "release_version" {
  type        = string
  description = "Release version used to force replacement in one sample resource."
  default     = "2026.07.05-1"
}
