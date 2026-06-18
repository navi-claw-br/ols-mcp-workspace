#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NAMESPACE="${NAMESPACE:-ols-mcp-server}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-ols-mcp-server}"
IMAGE_PULL_SECRET="${IMAGE_PULL_SECRET:-ghcr-pull}"
IMAGE="${IMAGE:-ghcr.io/navi-claw-br/rhcl-mcp-server:latest}"

echo "==> Ensuring namespace ${NAMESPACE}"
oc get namespace "${NAMESPACE}" >/dev/null 2>&1 || oc create namespace "${NAMESPACE}"

echo "==> Ensuring service account ${SERVICE_ACCOUNT}"
oc -n "${NAMESPACE}" get serviceaccount "${SERVICE_ACCOUNT}" >/dev/null 2>&1 || \
  oc -n "${NAMESPACE}" create serviceaccount "${SERVICE_ACCOUNT}"

if ! oc -n "${NAMESPACE}" get secret "${IMAGE_PULL_SECRET}" >/dev/null 2>&1; then
  echo "WARNING: imagePullSecret ${IMAGE_PULL_SECRET} not found in namespace ${NAMESPACE}"
  echo "The deployment may fail to pull ${IMAGE} until the secret exists."
fi

echo "==> Applying Service"
oc apply -f "${SCRIPT_DIR}/service.yaml"

echo "==> Applying Deployment"
oc apply -f "${SCRIPT_DIR}/deployment.yaml"

echo "==> Updating image to ${IMAGE}"
oc -n "${NAMESPACE}" set image deployment/rhcl-mcp-server rhcl-mcp-server="${IMAGE}"

echo "==> Setting service account to ${SERVICE_ACCOUNT}"
oc -n "${NAMESPACE}" patch deployment rhcl-mcp-server \
  --type merge \
  -p "{\"spec\":{\"template\":{\"spec\":{\"serviceAccountName\":\"${SERVICE_ACCOUNT}\",\"imagePullSecrets\":[{\"name\":\"${IMAGE_PULL_SECRET}\"}]}}}}"

echo "==> Waiting for rollout"
oc -n "${NAMESPACE}" rollout status deployment/rhcl-mcp-server --timeout=180s

echo
echo "RHCL MCP server deployed."
echo "Next:"
echo "  1. Apply ols-config/olsconfig.yaml if needed"
echo "  2. Validate with the runbook in docs/rhcl-mcp-server-runbook.md"
