#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="rvxai-491609"
REGION="europe-west1"
SERVICE_NAME="revox-api"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud run deploy "$SERVICE_NAME"   --source .   --region "$REGION"   --allow-unauthenticated   --port 8000   --set-env-vars ENABLE_DOCS=false

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

echo "Deployed to: $SERVICE_URL"
echo "Health: $SERVICE_URL/health"
echo "Privacy policy: $SERVICE_URL/privacy-policy"
echo "GPT OpenAPI: $SERVICE_URL/openapi-gpt.json"
