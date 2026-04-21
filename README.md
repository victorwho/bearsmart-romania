# Revox Routine API — Public Cloud Run build

API deterministic pentru filtrarea catalogului Revox și construirea unei rutine esențiale fără halucinații de produse.

## Setup țintă
- **Project ID**: `rvxai-491609`
- **Region**: `europe-west1`
- **Service**: `revox-api`
- **Runtime**: Google Cloud Run
- **Access model**: public HTTPS endpoint
- **GPT target**: public GPT in Store în viitor

## Ce face
- filtrează produsele strict din baza `database13_retaileri_moment2_IDProdus_NuCombinaCu_IDs.json`
- validează retailerul exact
- folosește `IDProdus` intern și afișează `NumeProdus` exact
- respectă `NuCombinaCu`
- aplică regulile de bază pentru retinol
- returnează linkul retailerului din `links.txt`
- expune un URL de privacy policy la `/privacy-policy`
- poate fi conectat ca Action în GPT Builder

## Endpointuri recomandate pentru GPT
- `GET /retailer-links/{retailer}`
- `GET /products/{product_id}`
- `POST /routine/recommend`

## Endpointuri utile de admin/test
- `GET /health`
- `GET /retailers`
- `GET /retailer-links`
- `POST /products/search`

## Local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Deploy public pe Cloud Run
Vezi:
- `gcp/SETUP_GOOGLE_CLOUD_PUBLIC.md`
- `gcp/deploy_public_cloud_run.sh`

## Privacy policy
- text editabil: `data/privacy_policy.md`
- URL public după deploy: `https://YOUR_CLOUD_RUN_URL/privacy-policy`

## GPT Builder
1. Deployezi serviciul public.
2. Importezi `openapi_for_gpt_public.yaml` sau direct `https://YOUR_CLOUD_RUN_URL/openapi-gpt.json`
3. În GPT Builder setezi Privacy Policy URL către `/privacy-policy`
4. În schema Action expui doar endpointurile necesare.

## Observație
Dacă în viitor trimiți selfie-ul brut către API, revizuiește politicile de confidențialitate și modelul de securitate înainte de publicare.
