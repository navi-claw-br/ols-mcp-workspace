#!/usr/bin/env bash
# deploy.sh - Deploy do openshift-mcp-server no cluster OpenShift
set -euo pipefail

NAMESPACE="${NAMESPACE:-kubernetes-mcp-server}"
CHART_REPO="${CHART_REPO:-https://github.com/openshift/openshift-mcp-server.git}"
CHART_PATH="${CHART_PATH:-../openshift-mcp-server/charts/kubernetes-mcp-server}"
VALUES_FILE="${VALUES_FILE:-values.yaml}"
CONFIG_TOML="${CONFIG_TOML:-config.toml}"

echo "=== Deploy do MCP Server para OpenShift Lightspeed ==="

# 1. Criar namespace
echo "[1/5] Criando namespace ${NAMESPACE}..."
oc create namespace "${NAMESPACE}" --dry-run=client -o yaml | oc apply -f -

# 2. Criar ConfigMap com config.toml
echo "[2/5] Criando ConfigMap de configuracao..."
oc create configmap kubernetes-mcp-server-config \
  --namespace "${NAMESPACE}" \
  --from-file=config.toml="${CONFIG_TOML}" \
  --dry-run=client -o yaml | oc apply -f -

# 3. Aplicar RBAC
echo "[3/5] Aplicando RBAC..."
oc apply -f rbac.yaml

# 4. Deploy via Helm
echo "[4/5] Instalando/atualizando Helm chart..."

# Verifica se o chart existe localmente ou clona
if [ ! -d "${CHART_PATH}" ]; then
  echo "Chart nao encontrado em ${CHART_PATH}. Clonando repositorio..."
  git clone --depth=1 "${CHART_REPO}" /tmp/openshift-mcp-server
  CHART_PATH="/tmp/openshift-mcp-server/charts/kubernetes-mcp-server"
fi

helm upgrade --install kubernetes-mcp-server "${CHART_PATH}" \
  --namespace "${NAMESPACE}" \
  --values "${VALUES_FILE}" \
  --wait \
  --timeout 5m

# 5. Verificar deploy
echo "[5/5] Verificando deploy..."
oc get pods -n "${NAMESPACE}"
oc get services -n "${NAMESPACE}"

echo ""
echo "=== Deploy concluido! ==="
echo "MCP Server URL: http://kubernetes-mcp-server.${NAMESPACE}.svc.cluster.local:8080/mcp"
echo ""
echo "Proximo passo: aplicar o OLSConfig"
echo "  oc apply -f ../ols-config/olsconfig.yaml"
