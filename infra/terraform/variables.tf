variable "project_id" {
  type        = string
  description = "The GCP project ID to deploy resources to"
  default     = "sandbox-500619"
}

variable "region" {
  type        = string
  description = "The GCP region for Cloud Run deployment"
  default     = "us-central1"
}

variable "service_name" {
  type        = string
  description = "Name of the Cloud Run service"
  default     = "breakaway-ai"
}
