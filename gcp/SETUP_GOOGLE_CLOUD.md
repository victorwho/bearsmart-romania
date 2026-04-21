# Deploy pe Google Cloud Run

## 1. Cerințe
- proiect GCP activ
- billing activ
- drepturi pentru Cloud Run, Cloud Build și Artifact Registry
- `gcloud` instalat local

## 2. Login și proiect
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## 3. Activează serviciile
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

## 4. Deploy rapid din source
Din directorul proiectului:
```bash
gcloud run deploy revox-api \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --port 8000
```

## 5. Verificare
După deploy, testează:
```bash
curl https://YOUR_CLOUD_RUN_URL/health
curl https://YOUR_CLOUD_RUN_URL/retailer-links
```

## 6. GPT Builder
În GPT Builder > Actions:
- importă `openapi_for_gpt.yaml` sau `https://YOUR_CLOUD_RUN_URL/openapi.json`
- dacă folosești schema locală, actualizează `servers.url` cu URL-ul Cloud Run

## 7. Recomandări
- dacă vei adăuga autentificare sau chei, pune-le în Secret Manager
- dacă publici GPT-ul în GPT Store și folosește Actions, vei avea nevoie și de un Privacy Policy URL
