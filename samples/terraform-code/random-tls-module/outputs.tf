output "name_suffix" {
  description = "Generated random suffix."
  value       = random_pet.suffix.id
}

output "private_key_pem" {
  value     = tls_private_key.deploy.private_key_pem
  sensitive = true
}
