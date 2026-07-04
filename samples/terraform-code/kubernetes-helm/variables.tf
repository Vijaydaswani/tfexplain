variable "kubeconfig_path" {
  type        = string
  description = "Path to kubeconfig."
  default     = "~/.kube/config"
}

variable "namespace" {
  type        = string
  description = "Application namespace."
  default     = "sample"
}

variable "replicas" {
  type        = number
  description = "Replica count."
  default     = 2

  validation {
    condition     = var.replicas >= 1
    error_message = "replicas must be at least 1."
  }
}
