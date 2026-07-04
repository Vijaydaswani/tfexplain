terraform {
  required_version = ">= 1.4.0"
}

locals {
  common_tags = {
    environment = var.environment
    owner       = var.owner
    service     = var.service_name
  }
}

resource "terraform_data" "service_config" {
  input = {
    name      = var.service_name
    replicas  = var.replicas
    reviewers = var.reviewers
    tags      = local.common_tags
  }
}

resource "terraform_data" "release_gate" {
  input = {
    service         = var.service_name
    release_version = var.release_version
  }

  triggers_replace = [
    var.release_version
  ]
}

resource "terraform_data" "review_context" {
  input = {
    high_attention = var.replicas > 3
    summary        = "${var.service_name} ${var.release_version}"
  }
}
