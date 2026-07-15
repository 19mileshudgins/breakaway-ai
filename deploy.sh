#!/bin/bash
set -e

PROJECT_ID="sandbox-500619"
REGION="us-central1"
SERVICE_NAME="breakaway-ai"

echo "=== Deploying BreakawayAI to Google Cloud Run ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"

# Build container image using Cloud Build
gcloud builds submit --project="${PROJECT_ID}" --tag="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest" .

# Deploy to Cloud Run with IAP or restricted access
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080

echo "=== Deployment Complete ==="
