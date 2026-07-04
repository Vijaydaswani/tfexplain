terraform {
  required_version = ">= 1.6.0"

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }

    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }

    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

resource "random_pet" "suffix" {
  length    = 2
  separator = "-"
}

resource "tls_private_key" "deploy" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "local_file" "public_key" {
  filename = "${path.module}/generated/${random_pet.suffix.id}.pub"
  content  = tls_private_key.deploy.public_key_openssh
}
