#!/usr/bin/env bash
# One-time Google Cloud setup for iom-cfd: APIs, Artifact Registry repo,
# results bucket, and a least-privilege service account for Batch VMs.
# Usage: cloud/gcp/setup.sh            (reads cloud/gcp/config.env)
# Safe to re-run: existing resources are left as they are.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source config.env

SA_NAME="${BATCH_SA%%@*}"
echo "project=$GCP_PROJECT region=$GCP_REGION bucket=gs://$GCS_BUCKET repo=$AR_REPO sa=$BATCH_SA"
read -r -p "Create/verify these resources? [y/N] " ok
[ "$ok" = "y" ] || exit 1

gcloud config set project "$GCP_PROJECT"
gcloud services enable batch.googleapis.com compute.googleapis.com logging.googleapis.com \
    artifactregistry.googleapis.com storage.googleapis.com

gcloud artifacts repositories describe "$AR_REPO" --location "$GCP_REGION" >/dev/null 2>&1 || \
    gcloud artifacts repositories create "$AR_REPO" --repository-format=docker \
        --location "$GCP_REGION" --description "IOM CFD solver images"

gcloud storage buckets describe "gs://$GCS_BUCKET" >/dev/null 2>&1 || \
    gcloud storage buckets create "gs://$GCS_BUCKET" --location "$GCP_REGION" --uniform-bucket-level-access

gcloud iam service-accounts describe "$BATCH_SA" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$SA_NAME" --display-name "iom-cfd Batch VMs"

# Batch agent + logs, pull images, read/write results
for role in roles/batch.agentReporter roles/logging.logWriter; do
    gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
        --member "serviceAccount:$BATCH_SA" --role "$role" --condition=None >/dev/null
done
gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location "$GCP_REGION" \
    --member "serviceAccount:$BATCH_SA" --role roles/artifactregistry.reader >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://$GCS_BUCKET" \
    --member "serviceAccount:$BATCH_SA" --role roles/storage.objectUser >/dev/null

# Let docker push to Artifact Registry from this machine
gcloud auth configure-docker "$GCP_REGION-docker.pkg.dev" --quiet

echo
echo "Done. Next: make push   (build + push the multi-arch image)"
echo "      iomcfd gcp submit foil2d/smoke --dry-run"
echo "Your own account also needs roles/batch.jobsEditor and roles/iam.serviceAccountUser on $BATCH_SA."
