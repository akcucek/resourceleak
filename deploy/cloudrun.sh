#!/usr/bin/env sh
# One-time + repeatable deploy to Google Cloud Run. Usage: PROJECT=my-proj REGION=asia-south1 sh deploy/cloudrun.sh
set -e
: "${PROJECT:?set PROJECT}"; REGION="${REGION:-asia-south1}"; SERVICE=resourceleak
gcloud config set project "$PROJECT"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com \
  places.googleapis.com bigquery.googleapis.com aiplatform.googleapis.com
# Secrets (paste the key when prompted). Restrict the Maps key to Places API (New) in the console.
[ -n "$GOOGLE_MAPS_API_KEY" ] && printf %s "$GOOGLE_MAPS_API_KEY" | gcloud secrets create maps-key --data-file=- 2>/dev/null || true
# BigQuery dataset + table for the impact ledger
bq --location=asia-south1 mk -d "$PROJECT:resourceleak" 2>/dev/null || true
bq mk -t "$PROJECT:resourceleak.impact_ledger" id:STRING,lot:STRING,route:STRING,qty:INTEGER,est:FLOAT,real:FLOAT,target:STRING 2>/dev/null || true
gcloud run deploy "$SERVICE" --source . --region "$REGION" --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT,BQ_DATASET=resourceleak,RL_DB=/tmp/resourceleak.sqlite3" \
  --set-secrets "GOOGLE_MAPS_API_KEY=maps-key:latest"
# Give the Cloud Run service account BigQuery write access:
#   gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:<run-sa> --role=roles/bigquery.dataEditor
