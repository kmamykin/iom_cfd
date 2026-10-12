#!/usr/bin/env bash
# One-time setup for the GitHub Actions image build (.github/workflows/image.yml):
# keyless access from GitHub to Artifact Registry via Workload Identity
# Federation. No service account keys are created.
#
#   - workload identity pool + GitHub OIDC provider, accepting only tokens from
#     pushes to main of GITHUB_REPO
#   - service account CI_SA with push access (artifactregistry.writer) to the
#     image repository only, which those tokens may impersonate
#   - GitHub repository variables the workflow reads (via the gh CLI)
#
# Usage: cloud/gcp/setup-github.sh [-y]   (reads cloud/gcp/config.env; run setup.sh first)
# Safe to re-run: existing resources are left as they are.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source config.env

if [ -z "${GITHUB_REPO:-}" ]; then  # owner/name from the origin remote
    GITHUB_REPO=$(git remote get-url origin | sed -E 's#^(git@|https://)github\.com[:/]##; s#\.git$##')
fi
WIF_POOL="${WIF_POOL:-github}"
WIF_PROVIDER="${WIF_PROVIDER:-github-actions}"
CI_SA="${CI_SA:-iom-cfd-ci@$GCP_PROJECT.iam.gserviceaccount.com}"

echo "project=$GCP_PROJECT repo=$GITHUB_REPO (branch main) pool=$WIF_POOL provider=$WIF_PROVIDER sa=$CI_SA"
echo "account=$(gcloud config get account 2>/dev/null)"
if [ "${1:-}" != "-y" ]; then
    if [ ! -t 0 ]; then
        echo "no terminal to confirm on: re-run with -y to create/verify these resources" >&2
        exit 1
    fi
    read -r -p "Create/verify these resources and set the GitHub repository variables? [y/N] " ok
    [ "$ok" = "y" ] || exit 1
fi

export CLOUDSDK_CORE_PROJECT="$GCP_PROJECT"
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)')

retry() {
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
        "$@" && return 0
        echo "  retrying in 10 s (new identities take a moment to propagate)" >&2
        sleep 10
    done
    return 1
}

gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com

gcloud iam workload-identity-pools describe "$WIF_POOL" --location global >/dev/null 2>&1 || \
    gcloud iam workload-identity-pools create "$WIF_POOL" --location global \
        --display-name "GitHub Actions"

gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER" \
    --workload-identity-pool "$WIF_POOL" --location global >/dev/null 2>&1 || \
    gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
        --workload-identity-pool "$WIF_POOL" --location global \
        --display-name "GitHub $GITHUB_REPO" \
        --issuer-uri "https://token.actions.githubusercontent.com" \
        --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
        --attribute-condition "assertion.repository == '$GITHUB_REPO' && assertion.ref == 'refs/heads/main'"

gcloud iam service-accounts describe "$CI_SA" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "${CI_SA%%@*}" --display-name "iom-cfd GitHub image builds"

retry gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location "$GCP_REGION" \
    --member "serviceAccount:$CI_SA" --role roles/artifactregistry.writer >/dev/null
POOL_ID="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WIF_POOL"
retry gcloud iam service-accounts add-iam-policy-binding "$CI_SA" \
    --member "principalSet://iam.googleapis.com/$POOL_ID/attribute.repository/$GITHUB_REPO" \
    --role roles/iam.workloadIdentityUser >/dev/null

PROVIDER_ID="$POOL_ID/providers/$WIF_PROVIDER"
declare -a VARS=(
    "GCP_PROJECT=$GCP_PROJECT"
    "GCP_REGION=$GCP_REGION"
    "AR_REPO=$AR_REPO"
    "IMAGE_NAME=${IMAGE_NAME:-iom-cfd}"
    "GCP_WIF_PROVIDER=$PROVIDER_ID"
    "GCP_CI_SA=$CI_SA"
)
echo
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
    for kv in "${VARS[@]}"; do
        gh variable set "${kv%%=*}" --repo "$GITHUB_REPO" --body "${kv#*=}"
    done
    echo "Set GitHub repository variables on $GITHUB_REPO."
else
    echo "gh CLI not available or not logged in; set these repository variables on GitHub"
    echo "(Settings > Secrets and variables > Actions > Variables):"
    printf '  %s\n' "${VARS[@]}"
fi
echo
echo "Done. The next push to main builds and pushes the image (or run the workflow"
echo "by hand: gh workflow run image.yml --repo $GITHUB_REPO)."
