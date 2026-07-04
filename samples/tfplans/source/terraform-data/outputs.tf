output "service_config_id" {
  description = "ID of the service configuration sample resource."
  value       = terraform_data.service_config.id
}

output "release_gate_id" {
  description = "ID of the release gate sample resource."
  value       = terraform_data.release_gate.id
}

output "review_context_id" {
  description = "ID of the review context sample resource."
  value       = terraform_data.review_context.id
}
