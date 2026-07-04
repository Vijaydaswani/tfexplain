output "generated_name" {
  description = "Generated deterministic service name."
  value       = terraform_data.generated_name.output.value
}

output "service_config" {
  description = "Service configuration sample output."
  value       = terraform_data.service_config.output
}

output "release_gate_id" {
  description = "Release gate resource ID."
  value       = terraform_data.release_gate.id
}
