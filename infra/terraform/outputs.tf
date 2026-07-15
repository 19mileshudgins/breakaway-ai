output "service_url" {
  value       = google_cloud_run_v2_service.breakaway_ai_service.uri
  description = "The deployed Cloud Run service URL"
}

output "service_name" {
  value       = google_cloud_run_v2_service.breakaway_ai_service.name
  description = "The Cloud Run service name"
}
