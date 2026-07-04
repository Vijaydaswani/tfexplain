output "namespace" {
  description = "Created namespace."
  value       = kubernetes_namespace.app.metadata[0].name
}
