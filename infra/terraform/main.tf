terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable GCP Cloud Run API
resource "google_project_service" "cloud_run_api" {
  project                    = var.project_id
  service                    = "run.googleapis.com"
  disable_on_destroy         = false
}

# Cloud Run Service for BreakawayAI Agent
resource "google_cloud_run_v2_service" "breakaway_ai_service" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "gcr.io/${var.project_id}/${var.service_name}:latest"
      
      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }

      env {
        name  = "MODEL_NAME"
        value = "gemini-2.5-flash"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
  }

  depends_on = [google_project_service.cloud_run_api]
}

# Allow unauthenticated invocation for submission assessment
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.breakaway_ai_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
