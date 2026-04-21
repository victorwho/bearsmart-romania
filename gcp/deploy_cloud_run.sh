#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-YOUR_PROJECT_ID}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-revox-api}"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8000

echo "Deployed. Test with:"
echo "curl https://$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')/health"
