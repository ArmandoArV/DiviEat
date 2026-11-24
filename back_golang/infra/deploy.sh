#!/usr/bin/env bash
# Deploys the CoDi API to Azure Container Apps.
#
# Two passes on purpose: the registry has to exist before there is anywhere
# to push the image, and the image has to exist before the app can run it.
#
#   SUBSCRIPTION=<id-or-name> ./infra/deploy.sh
#
# Secrets come from the environment, never from a file in the repo:
#   PEY_API_KEY, PEY_WEBHOOK_SECRET, MONGODB_URI
set -euo pipefail

cd "$(dirname "$0")/.."

: "${SUBSCRIPTION:?set SUBSCRIPTION to the subscription id or name}"
: "${PEY_API_KEY:?set PEY_API_KEY}"
: "${PEY_WEBHOOK_SECRET:?set PEY_WEBHOOK_SECRET}"
: "${MONGODB_URI:?set MONGODB_URI, or pass deployDatabase=true to create Cosmos}"

LOCATION="${LOCATION:-centralus}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%s)}"

az account set --subscription "$SUBSCRIPTION"
echo "==> subscription: $(az account show --query name -o tsv)"

# --- pass 1: infrastructure, with whatever image is already configured ----
echo "==> deploying infrastructure"
az deployment sub create \
  --name "divieat-infra-$TAG" \
  --location "$LOCATION" \
  --parameters infra/main.bicepparam \
  --output none

REGISTRY=$(az deployment sub show --name "divieat-infra-$TAG" \
  --query properties.outputs.registryLoginServer.value -o tsv)

# --- build and push -------------------------------------------------------
# Built in ACR rather than locally: no Docker daemon needed, and the image is
# produced for linux/amd64 regardless of what this laptop is.
echo "==> building $REGISTRY/codi-api:$TAG in the registry"
az acr build \
  --registry "${REGISTRY%%.*}" \
  --image "codi-api:$TAG" \
  --file Dockerfile . \
  --output none

# --- pass 2: point the app at the image just built ------------------------
echo "==> deploying the app"
az deployment sub create \
  --name "divieat-app-$TAG" \
  --location "$LOCATION" \
  --parameters infra/main.bicepparam \
  --parameters image="$REGISTRY/codi-api:$TAG" \
  --output none

API_URL=$(az deployment sub show --name "divieat-app-$TAG" \
  --query properties.outputs.apiUrl.value -o tsv)
WEBHOOK=$(az deployment sub show --name "divieat-app-$TAG" \
  --query properties.outputs.webhookUrl.value -o tsv)

echo
echo "API:      $API_URL"
echo "health:   $API_URL/health"
echo "webhook:  $WEBHOOK"
echo
echo "Register that webhook URL in the Pey portal, under the gear next to the API key."
