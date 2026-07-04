output "service_uri" {
  description = "Cloud Run service URI."
  value       = google_cloud_run_v2_service.api.uri
}
