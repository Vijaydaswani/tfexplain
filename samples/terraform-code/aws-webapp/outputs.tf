output "instance_id" {
  description = "Created EC2 instance ID."
  value       = aws_instance.web.id
}

output "security_group_id" {
  description = "Security group ID."
  value       = aws_security_group.web.id
}
