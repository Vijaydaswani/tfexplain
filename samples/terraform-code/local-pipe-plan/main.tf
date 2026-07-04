terraform {
  required_version = ">= 1.4.0"
}

locals {
  name_seed = "${var.service_name}-${var.environment}-${var.owner}"
  suffix    = substr(sha256(local.name_seed), 0, 8)

  labels = {
    environment = var.environment
    owner       = var.owner
    service     = var.service_name
  }
}

resource "terraform_data" "generated_name" {
  input = {
    value = "${var.service_name}-${local.suffix}"
    seed  = local.name_seed
  }
}

resource "terraform_data" "service_config" {
  input = {
    name     = terraform_data.generated_name.output.value
    replicas = var.replicas
    labels   = local.labels
  }
}

resource "terraform_data" "release_gate" {
  input = {
    release_version = var.release_version
    service_name    = var.service_name
  }

  triggers_replace = [
    var.release_version
  ]
}
