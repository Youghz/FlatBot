output "web_url" {
  description = "URL of the web app"
  value       = google_cloud_run_v2_service.web.uri
}

output "scraper_job" {
  description = "Cloud Run Job name"
  value       = google_cloud_run_v2_job.scraper.name
}

output "db_instance" {
  description = "Cloud SQL instance connection name"
  value       = local.db_connection
}

output "db_connection_url" {
  description = "Database URL (sensitive)"
  value       = local.database_url
  sensitive   = true
}
