# Deploy public pe Google Cloud Run

## Parametri fixați
- Project ID: `rvxai-491609`
- Region: `europe-west1`
- Service: `revox-api`

## 1. Login și proiect
```bash
gcloud auth login
gcloud config set project rvxai-491609
```

## 2. Activează serviciile
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

## 3. Deploy din source
Din directorul proiectului:
```bash
gcloud run deploy revox-api   --source .   --region europe-west1   --allow-unauthenticated   --port 8000   --set-env-vars ENABLE_DOCS=false
```

## 4. Obține URL-ul
```bash
gcloud run services describe revox-api   --region europe-west1   --format='value(status.url)'
```

## 5. Verificare
```bash
curl https://YOUR_CLOUD_RUN_URL/health
curl https://YOUR_CLOUD_RUN_URL/privacy-policy
curl https://YOUR_CLOUD_RUN_URL/openapi-gpt.json
```

## 6. GPT Builder
- Importă `https://YOUR_CLOUD_RUN_URL/openapi-gpt.json`
- Sau folosește fișierul `openapi_for_gpt_public.yaml`
- Privacy Policy URL: `https://YOUR_CLOUD_RUN_URL/privacy-policy`

## 7. Recomandare practică
În GPT Store, expune în schema Action doar endpointurile de care GPT-ul are nevoie.
