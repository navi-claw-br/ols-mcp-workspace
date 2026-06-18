# Guia de Deploy Completo

Este guia descreve o passo a passo para configurar o OpenShift Lightspeed com um MCP Server para executar comandos no OpenShift com as permissões do usuário logado.

## Pré-requisitos

- Cluster OpenShift 4.16+
- Acesso cluster-admin via `oc`
- `helm` CLI instalado
- OpenShift Lightspeed Operator 1.0 instalado
- LLM Provider (OpenAI, Vertex AI, etc.)

## Passo 1: Instalar o OpenShift Lightspeed Operator

```bash
# Verificar se o operator ja esta instalado
oc get pods -n openshift-lightspeed

# Se nao estiver, instalar via OperatorHub
# OpenShift Console → Operators → OperatorHub → "OpenShift Lightspeed"
```

## Passo 2: Criar Credenciais do LLM

### OpenAI
```bash
oc create secret generic openai \
  --namespace openshift-lightspeed \
  --from-literal=apitoken="sk-..."
```

### Google Vertex AI
```bash
# Credenciais ADC
ADC="$HOME/.config/gcloud/application_default_credentials.json"

for s in gcp-credentials gcp-credentials-anthropic; do
  oc create secret generic "$s" \
    --namespace openshift-lightspeed \
    --from-file=apitoken="$ADC"
done
```

## Passo 3: Deploy do MCP Server

O MCP server usado é o [openshift-mcp-server](https://github.com/openshift/openshift-mcp-server) oficial da Red Hat.

### Opção A: Deploy via Helm (recomendado)

```bash
# Clonar o repositorio
git clone https://github.com/openshift/openshift-mcp-server.git /tmp/openshift-mcp-server

# Instalar via Helm
helm upgrade --install kubernetes-mcp-server \
  /tmp/openshift-mcp-server/charts/kubernetes-mcp-server \
  -n kubernetes-mcp-server --create-namespace \
  -f mcp-server/values.yaml
```

### Opção B: Deploy manual

```bash
# Criar namespace
oc new-project kubernetes-mcp-server

# Aplicar RBAC
oc apply -f mcp-server/rbac.yaml

# Criar ConfigMap
oc create configmap kubernetes-mcp-server-config \
  -n kubernetes-mcp-server \
  --from-file=mcp-server/config.toml

# Deploy da aplicacao
oc apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kubernetes-mcp-server
  namespace: kubernetes-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kubernetes-mcp-server
  template:
    metadata:
      labels:
        app: kubernetes-mcp-server
    spec:
      serviceAccountName: kubernetes-mcp-server
      containers:
        - name: kubernetes-mcp-server
          image: quay.io/openshift/kubernetes-mcp-server:latest
          args:
            - --port=8080
            - --log-level=2
            - --config=/etc/kubernetes-mcp-server/config.toml
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: config
              mountPath: /etc/kubernetes-mcp-server
      volumes:
        - name: config
          configMap:
            name: kubernetes-mcp-server-config
---
apiVersion: v1
kind: Service
metadata:
  name: kubernetes-mcp-server
  namespace: kubernetes-mcp-server
spec:
  selector:
    app: kubernetes-mcp-server
  ports:
    - port: 8080
      targetPort: 8080
EOF
```

### Verificar deploy

```bash
oc get pods -n kubernetes-mcp-server
oc get service kubernetes-mcp-server -n kubernetes-mcp-server
```

## Passo 3B: Deploy do RHCL MCP Server customizado

Use este passo se quiser tools especializadas para Gateway API e Kuadrant,
além do `openshift-mcp-server` genérico.

```bash
cd rhcl-mcp-server
podman build -t ghcr.io/navi-claw-br/rhcl-mcp-server:latest .
podman push ghcr.io/navi-claw-br/rhcl-mcp-server:latest
./deploy.sh
```

Verificar:

```bash
oc -n ols-mcp-server get deploy,pod,svc | grep rhcl-mcp-server
```

O runbook detalhado está em `docs/rhcl-mcp-server-runbook.md`.

## Passo 4: Configurar o Lightspeed

```bash
# Aplicar o OLSConfig
oc apply -f ols-config/olsconfig.yaml

# Verificar se foi aceito
oc get olsconfig cluster -o yaml
```

## Passo 5: Conceder Acesso aos Usuários

```bash
# Para cada usuario que usara o Lightspeed
USER="$(oc whoami)"

# Acesso ao Lightspeed
oc adm policy add-cluster-role-to-user ols-user "${USER}"

# Permissoes de visualizacao
oc adm policy add-cluster-role-to-user view "${USER}"
oc adm policy add-cluster-role-to-user cluster-monitoring-view "${USER}"
```

## Passo 6: Testar

```bash
# Obter URL do Lightspeed
OLS_HOST=$(oc get route lightspeed-app-server -n openshift-lightspeed -o jsonpath='{.spec.host}')

# Obter token
TOKEN=$(oc whoami -t)

# Testar query direta
curl -k -X POST "https://${OLS_HOST}/v1/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query": "List all pods in the openshift-lightspeed namespace"}'
```

## Troubleshooting

### MCP server nao consegue autenticar

Verifique se o OLSConfig esta configurado com `valueFrom.type: kubernetes`:
```bash
oc get olsconfig cluster -o jsonpath='{.spec.mcpServers[0].headers}' | jq .
```

### Lightspeed retorna 403

O usuario nao tem o role `ols-user`:
```bash
oc adm policy add-cluster-role-to-user ols-user <usuario>
```

### MCP tool timeout

Aumente o timeout no OLSConfig:
```yaml
mcpServers:
  - name: openshift-mcp-server
    url: http://...
    timeout: 120  # segundos
```

### MCP server retorna "forbidden"

O usuario nao tem permissao para a operacao solicitada. Conceda as Roles necessarias no OpenShift.

### RHCL MCP server retorna erro com service account

Se o erro citar `system:serviceaccount:ols-mcp-server:ols-mcp-server`,
o problema nao e RBAC do usuario. Isso indica que o passthrough do token
nao chegou na operacao de escrita. Confira:

```bash
oc get olsconfig cluster -o jsonpath='{.spec.mcpServers}' | jq .
```

E siga `docs/rhcl-mcp-server-runbook.md`.
