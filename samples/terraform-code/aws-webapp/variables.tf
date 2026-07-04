variable "region" {
  type        = string
  description = "AWS region for the web application."
  default     = "us-east-1"

  validation {
    condition     = length(var.region) > 0
    error_message = "region must not be empty."
  }
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
  default     = "dev"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type."
  default     = "t3.micro"
}

variable "allowed_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}
