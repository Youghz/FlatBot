#!/bin/bash
# =============================================================
# Deploy FlatBot to GCP: Cloud Run Service + Job + Cloud SQL
# =============================================================
set -e

PROJECT_ID="sandbox-hugo"
REGION="northamerica-northeast1"  # Montreal
SERVICE_ACCOUNT="flat-research@${PROJECT_ID}.iam.gserviceaccount.com"
REPO_NAME="flat-research"
WEB_SERVICE="flatbot-web"
SCRAPER_JOB="flatbot-scraper"
DB_INSTANCE="flatbot-db"
DB_NAME="flatbot"
WEB_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/flatbot-web:latest"
SCRAPER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/flatbot-scraper:latest"
DB_CONNECTION="${PROJECT_ID}:${REGION}:${DB_INSTANCE}"

echo "=== 1. Enable required APIs ==="
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  --project="${PROJECT_ID}"

echo "=== 2. Create Artifact Registry repo ==="
gcloud artifacts repositories create "${REPO_NAME}" \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  2>/dev/null || echo "Repo already exists"

echo "=== 3. Create Cloud SQL instance ==="
gcloud sql instances describe "${DB_INSTANCE}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1 || \
gcloud sql instances create "${DB_INSTANCE}" \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --storage-auto-increase \
  --no-assign-ip \
  --network=default

gcloud sql databases create "${DB_NAME}" \
  --instance="${DB_INSTANCE}" \
  --project="${PROJECT_ID}" \
  2>/dev/null || echo "Database already exists"

echo "=== 4. Set Cloud SQL password ==="
# Read .env for secrets
while IFS='=' read -r key value; do
  [[ -z "$key" || "$key" =~ ^# ]] && continue
  export "$key"="$value"
done < .env

DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 16)}"
gcloud sql users set-password postgres \
  --instance="${DB_INSTANCE}" \
  --password="${DB_PASSWORD}" \
  --project="${PROJECT_ID}"

DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${DB_CONNECTION}"

echo "=== 5. Store secrets in Secret Manager ==="
_upsert_secret() {
  local name=$1 value=$2
  echo -n "${value}" | gcloud secrets create "${name}" \
    --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
  echo -n "${value}" | gcloud secrets versions add "${name}" \
    --data-file=- --project="${PROJECT_ID}"
  gcloud secrets add-iam-policy-binding "${name}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="${PROJECT_ID}" --quiet
}

JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"

_upsert_secret "database-url" "${DATABASE_URL}"
_upsert_secret "jwt-secret-key" "${JWT_SECRET_KEY}"
_upsert_secret "telegram-bot-token" "${TELEGRAM_BOT_TOKEN}"

echo "=== 6. Grant IAM roles to service account ==="
for ROLE in roles/run.invoker roles/cloudscheduler.admin roles/cloudsql.client; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${ROLE}" --quiet
done

echo "=== 7. Build & push images ==="
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

docker build --target web -t "${WEB_IMAGE}" .
docker push "${WEB_IMAGE}"

docker build --target scraper -t "${SCRAPER_IMAGE}" .
docker push "${SCRAPER_IMAGE}"

SECRETS_FLAG="DATABASE_URL=database-url:latest,JWT_SECRET_KEY=jwt-secret-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest"

echo "=== 8. Deploy web service ==="
gcloud run deploy "${WEB_SERVICE}" \
  --image="${WEB_IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-secrets="${SECRETS_FLAG}" \
  --add-cloudsql-instances="${DB_CONNECTION}" \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=3

echo "=== 9. Deploy scraper job ==="
gcloud run jobs create "${SCRAPER_JOB}" \
  --image="${SCRAPER_IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-secrets="${SECRETS_FLAG}" \
  --set-cloudsql-instances="${DB_CONNECTION}" \
  --memory=512Mi \
  --task-timeout=300s \
  --max-retries=1 \
  2>/dev/null || \
gcloud run jobs update "${SCRAPER_JOB}" \
  --image="${SCRAPER_IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-secrets="${SECRETS_FLAG}" \
  --set-cloudsql-instances="${DB_CONNECTION}" \
  --memory=512Mi \
  --task-timeout=300s \
  --max-retries=1

echo "=== 10. Create Cloud Scheduler (hourly scrape) ==="
gcloud scheduler jobs create http "${SCRAPER_JOB}-schedule" \
  --location="${REGION}" \
  --schedule="17 * * * *" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SCRAPER_JOB}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  2>/dev/null || \
gcloud scheduler jobs update http "${SCRAPER_JOB}-schedule" \
  --location="${REGION}" \
  --schedule="17 * * * *" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${SCRAPER_JOB}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}"

echo "=== 11. Run Alembic migration ==="
# Run migration via a one-off Cloud Run job execution
gcloud run jobs execute "${SCRAPER_JOB}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --args="alembic,upgrade,head" \
  --wait || echo "Migration may need manual run"

WEB_URL=$(gcloud run services describe "${WEB_SERVICE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(status.url)")

echo ""
echo "=== Done! ==="
echo "Web app: ${WEB_URL}"
echo "Scraper job: https://console.cloud.google.com/run/jobs/details/${REGION}/${SCRAPER_JOB}?project=${PROJECT_ID}"
echo "Scheduler: https://console.cloud.google.com/cloudscheduler?project=${PROJECT_ID}"
echo "Cloud SQL: https://console.cloud.google.com/sql/instances/${DB_INSTANCE}?project=${PROJECT_ID}"
echo ""
echo "Manual scrape: gcloud run jobs execute ${SCRAPER_JOB} --region=${REGION} --project=${PROJECT_ID}"
