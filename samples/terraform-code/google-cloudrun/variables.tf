variable "project_id" {
  type        = string
  description = "Google Cloud project ID."
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "service_name" {
  type        = string
  description = "Cloud Run service name."
  default     = "sample-api"
}

variable "image" {
  type        = string
  description = "Container image."
}

variable "environment" {
  type        = string
  description = "Runtime environment."
  default     = "dev"
}
