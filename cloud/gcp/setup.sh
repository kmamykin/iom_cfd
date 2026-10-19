#!/usr/bin/env bash
# One-time Google Cloud setup for iom-cfd: APIs, Artifact Registry repo,
# results bucket, and a least-privilege service account for Batch VMs.
# Usage: cloud/gcp/setup.sh [-y]       (reads cloud/gcp/config.env; -y skips the prompt)
# Safe to re-run: existing resources are left as they are.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source config.env

SA_NAME="${BATCH_SA%%@*}"
echo "project=$GCP_PROJECT region=$GCP_REGION bucket=gs://$GCS_BUCKET repo=$AR_REPO sa=$BATCH_SA"
echo "account=$(gcloud config get account 2>/dev/null)"
if [ "${1:-}" != "-y" ]; then
    if [ ! -t 0 ]; then
        echo "no terminal to confirm on: re-run with -y to create/verify these resources" >&2
        exit 1
    fi
    read -r -p "Create/verify these resources? [y/N] " ok
    [ "$ok" = "y" ] || exit 1
fi

# Scope the project to this script; the active gcloud configuration is left alone.
export CLOUDSDK_CORE_PROJECT="$GCP_PROJECT"
gcloud services enable batch.googleapis.com compute.googleapis.com logging.googleapis.com \
    artifactregistry.googleapis.com storage.googleapis.com

gcloud artifacts repositories describe "$AR_REPO" --location "$GCP_REGION" >/dev/null 2>&1 || \
    gcloud artifacts repositories create "$AR_REPO" --repository-format=docker \
        --location "$GCP_REGION" --description "IOM CFD solver images"

gcloud storage buckets describe "gs://$GCS_BUCKET" >/dev/null 2>&1 || \
    gcloud storage buckets create "gs://$GCS_BUCKET" --location "$GCP_REGION" --uniform-bucket-level-access

# Batch VMs have no external IP (gcp.py): they reach Google APIs this way
gcloud compute networks subnets update default --region "$GCP_REGION" --enable-private-ip-google-access

gcloud iam service-accounts describe "$BATCH_SA" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "$SA_NAME" --display-name "iom-cfd Batch VMs"

# A new service account takes a little while to be visible to IAM policies.
retry() {
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
        "$@" && return 0
        echo "  retrying in 10 s (new service accounts take a moment to propagate)" >&2
        sleep 10
    done
    return 1
}

# Batch agent + logs, pull images, read/write results
for role in roles/batch.agentReporter roles/logging.logWriter; do
    retry gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
        --member "serviceAccount:$BATCH_SA" --role "$role" --condition=None >/dev/null
done
retry gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location "$GCP_REGION" \
    --member "serviceAccount:$BATCH_SA" --role roles/artifactregistry.reader >/dev/null
retry gcloud storage buckets add-iam-policy-binding "gs://$GCS_BUCKET" \
    --member "serviceAccount:$BATCH_SA" --role roles/storage.objectUser >/dev/null

# Let docker push to Artifact Registry from this machine
gcloud auth configure-docker "$GCP_REGION-docker.pkg.dev" --quiet

echo
echo "Done. Next: cloud/gcp/setup-github.sh   (image builds on every branch push; or make push-amd64)"
echo "      iomcfd gcp submit foil2d/smoke --dry-run"
echo "Your own account also needs roles/batch.jobsEditor and roles/iam.serviceAccountUser on $BATCH_SA."
