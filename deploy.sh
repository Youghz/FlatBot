#!/bin/bash
# =============================================================
# Deploy Flat Research to GCP Cloud Run Jobs + Cloud Scheduler
# =============================================================
set -e

PROJECT_ID="sandbox-hugo"
REGION="northamerica-northeast1"  # Montreal
SERVICE_ACCOUNT="flat-research@${PROJECT_ID}.iam.gserviceaccount.com"
JOB_NAME="flat-research"
REPO_NAME="flat-research"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${JOB_NAME}:latest"

echo "=== 1. Enable required APIs ==="
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT_ID}"

echo "=== 2. Grant IAM roles to service account ==="
for ROLE in roles/run.invoker roles/cloudscheduler.admin; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${ROLE}" --quiet
done

echo "=== 2b. Enable Sheets/Drive APIs and grant SA domain-wide access ==="
gcloud services enable \
  sheets.googleapis.com \
  drive.googleapis.com \
  --project="${PROJECT_ID}"

echo "=== 3. Create Artifact Registry repo ==="
gcloud artifacts repositories create "${REPO_NAME}" \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  2>/dev/null || echo "Repo already exists"

echo "=== 4. Build & push image via Cloud Build ==="
gcloud builds submit \
  --tag="${IMAGE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}"

echo "=== 6. Store Telegram secrets in Secret Manager ==="
source .env

# Create or update secrets
echo -n "${TELEGRAM_BOT_TOKEN}" | gcloud secrets create telegram-bot-token \
  --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
echo -n "${TELEGRAM_BOT_TOKEN}" | gcloud secrets versions add telegram-bot-token \
  --data-file=- --project="${PROJECT_ID}"

echo -n "${TELEGRAM_CHAT_ID}" | gcloud secrets create telegram-chat-id \
  --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
echo -n "${TELEGRAM_CHAT_ID}" | gcloud secrets versions add telegram-chat-id \
  --data-file=- --project="${PROJECT_ID}"

echo -n "${GOOGLE_SPREADSHEET_ID}" | gcloud secrets create google-spreadsheet-id \
  --data-file=- --project="${PROJECT_ID}" 2>/dev/null || \
echo -n "${GOOGLE_SPREADSHEET_ID}" | gcloud secrets versions add google-spreadsheet-id \
  --data-file=- --project="${PROJECT_ID}"

# Grant service account access to secrets
gcloud secrets add-iam-policy-binding google-spreadsheet-id \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project="${PROJECT_ID}" --quiet

gcloud secrets add-iam-policy-binding telegram-bot-token \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project="${PROJECT_ID}" --quiet

gcloud secrets add-iam-policy-binding telegram-chat-id \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project="${PROJECT_ID}" --quiet

echo "=== 7. Create Cloud Run Job ==="
gcloud run jobs create "${JOB_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-secrets="TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CHAT_ID=telegram-chat-id:latest,GOOGLE_SPREADSHEET_ID=google-spreadsheet-id:latest" \
  --memory=512Mi \
  --task-timeout=300s \
  --max-retries=1 \
  2>/dev/null || \
gcloud run jobs update "${JOB_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --set-secrets="TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CHAT_ID=telegram-chat-id:latest,GOOGLE_SPREADSHEET_ID=google-spreadsheet-id:latest" \
  --memory=512Mi \
  --task-timeout=300s \
  --max-retries=1

echo "=== 8. Create Cloud Scheduler ==="
gcloud scheduler jobs create http "${JOB_NAME}-schedule" \
  --location="${REGION}" \
  --schedule="17 * * * *" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  2>/dev/null || \
gcloud scheduler jobs update http "${JOB_NAME}-schedule" \
  --location="${REGION}" \
  --schedule="17 * * * *" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --oauth-service-account-email="${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}"

echo "=== 9. Smoke test ==="
echo "Running health check on Cloud Run..."
gcloud run jobs execute "${JOB_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --args="--check" \
  --wait

EXECUTION_STATUS=$(gcloud run jobs executions list \
  --job="${JOB_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --limit=1 \
  --format="value(status.conditions[0].type)")

if [ "${EXECUTION_STATUS}" = "Completed" ]; then
  echo "Smoke test PASSED"
else
  echo "WARNING: Smoke test may have failed. Check logs:"
  echo "  gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
fi

echo ""
echo "=== Done! ==="
echo "Job: https://console.cloud.google.com/run/jobs/details/${REGION}/${JOB_NAME}?project=${PROJECT_ID}"
echo "Scheduler: https://console.cloud.google.com/cloudscheduler?project=${PROJECT_ID}"
echo ""
echo "Manual run: gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
