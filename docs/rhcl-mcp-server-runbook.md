# Runbook - RHCL MCP Server

Este runbook documenta como construir, publicar, deployar e validar o
`rhcl-mcp-server`, além do troubleshooting para o caso em que o MCP passa
a usar a service account do pod em vez do token do usuário.

## Objetivo

Garantir que operações RHCL feitas pelo Lightspeed:

- recebam o token do usuário no header `Authorization`
- executem `oc` com `--token <token>`
- respeitem o RBAC do usuário logado
- não caiam no contexto da service account `ols-mcp-server`
- não criem `HTTPRoute` externa sem `hostname`
- garantam `DNSPolicy` no `Gateway` quando a aplicacao for publicada via FQDN

## Arquivos envolvidos

- `rhcl-mcp-server/rhcl_server.py`
- `rhcl-mcp-server/Dockerfile`
- `rhcl-mcp-server/deployment.yaml`
- `rhcl-mcp-server/service.yaml`
- `rhcl-mcp-server/deploy.sh`
- `ols-config/olsconfig.yaml`
- `docs/mcp-auth.md`

## Sintoma do bug original

Ao pedir para o Lightspeed criar um `HTTPRoute`, a resposta vinha com erro
semelhante a:

```text
forbidden:
system:serviceaccount:ols-mcp-server:ols-mcp-server cannot create resource "httproutes"
```

Esse erro indicava que a operação de escrita não estava usando o token do
usuário e sim a service account do pod.

## Causa raiz

O servidor já usava passthrough para leitura, mas não para escrita:

- `run_oc()` montava `oc --token <token> ...`
- `oc_get_resource()` usava `run_oc()`
- `oc_create_resource()` executava `["oc"] + args` diretamente

Resultado:

- `get/list` respeitavam o RBAC do usuário
- `create` usava o contexto padrão do pod

## Correção aplicada

No `rhcl_server.py`:

1. `set_user_token()` passou a limpar o token quando não houver bearer header
2. `oc_create_resource()` passou a usar `get_oc_args(args)`
3. cada requisição HTTP zera o token antes de ler o header `Authorization`
4. `create_httproute` passou a exigir um hostname resolvido e usar `apply`
5. `create_dnspolicy` passou a garantir `DNSPolicy` por `Gateway`
6. `expose_service` passou a ser a tool preferida para deixar a API funcionando
7. `hostname` pode ser informado diretamente ou derivado de `dns_suffix`

## Pré-requisitos

- acesso `cluster-admin`
- `oc` autenticado no cluster
- `podman` autenticado no `ghcr.io`
- secret `ghcr-pull` no namespace `ols-mcp-server`
- service account `ols-mcp-server`

## Passo 1 - Build da imagem

```bash
cd rhcl-mcp-server
podman build -t ghcr.io/navi-claw-br/rhcl-mcp-server:latest .
```

## Passo 2 - Push da imagem

```bash
podman push ghcr.io/navi-claw-br/rhcl-mcp-server:latest
```

## Passo 3 - Deploy do servidor

Use o script do repositório:

```bash
cd rhcl-mcp-server
./deploy.sh
```

O script:

1. garante o namespace
2. garante a service account
3. aplica `service.yaml`
4. aplica `deployment.yaml`
5. atualiza a imagem
6. aguarda o rollout

## Passo 4 - Configurar o OLSConfig

O `ols-config/olsconfig.yaml` precisa conter a entrada do `rhcl-mcp-server`
com passthrough do header `Authorization`:

```yaml
  - name: rhcl-mcp-server
    url: http://rhcl-mcp-server.ols-mcp-server.svc.cluster.local:8080
    timeout: 120
    headers:
      - name: Authorization
        valueFrom:
          type: kubernetes
```

Aplicar:

```bash
oc apply -f ols-config/olsconfig.yaml
```

## Passo 5 - Validar que o pod subiu

```bash
oc -n ols-mcp-server get deploy,pod,svc | grep rhcl-mcp-server
oc -n ols-mcp-server rollout status deployment/rhcl-mcp-server --timeout=180s
```

## Passo 6 - Validar o endpoint HTTP

```bash
oc -n ols-mcp-server port-forward service/rhcl-mcp-server 18081:8080
curl -sS http://127.0.0.1:18081/
curl -sS \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  http://127.0.0.1:18081/
```

O `GET /` deve mostrar nome, versão e tools. O `tools/list` deve retornar:

- `list_gateways`
- `list_httproutes`
- `list_authpolicies`
- `list_ratelimitpolicies`
- `list_dnspolicies`
- `list_tlspolicies`
- `get_gateway_status`
- `create_httproute`
- `create_dnspolicy`
- `expose_service`
- `create_authpolicy`

## Passo 7 - Validar passthrough do token em escrita

Exemplo real usado para validar o fluxo autonomo:

```bash
TOKEN="$(oc whoami -t)"

cat <<'JSON' >/tmp/mcp-expose-service.json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "expose_service",
    "arguments": {
      "namespace": "debugocp3",
      "service": "debugocp",
      "route_name": "mcp-test-debugocp",
      "hostname": "debugocp.poc.rhcl.com.br",
      "port": 8080,
      "gateway": "rhcl-apps-gateway",
      "gateway_namespace": "openshift-ingress",
      "ensure_dns_policy": true
    }
  }
}
JSON

curl -sS \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  --data @/tmp/mcp-expose-service.json \
  http://127.0.0.1:18081/
```

Confirmar no cluster:

```bash
oc -n debugocp3 get httproute mcp-test-debugocp
oc -n debugocp3 get httproute mcp-test-debugocp -o yaml | rg hostnames -n
oc -n openshift-ingress get dnspolicies.kuadrant.io
```

## Passo 8 - Limpeza do teste

```bash
oc -n debugocp3 delete httproute mcp-test-debugocp
```

## Como interpretar falhas

### Caso 1 - erro cita a service account do pod

Exemplo:

```text
system:serviceaccount:ols-mcp-server:ols-mcp-server cannot create httproutes
```

Isso indica bug de passthrough ou ausência do header `Authorization`.

Checklist:

1. conferir se `oc_create_resource()` usa `get_oc_args(args)`
2. conferir se o `OLSConfig` tem `valueFrom.type: kubernetes`
3. conferir se a chamada ao MCP inclui `Authorization: Bearer <token>`
4. reiniciar o deployment com a imagem nova

### Caso 1B - HTTPRoute criada sem hostname

Isso e um erro de comportamento do assistente. Para exposicao externa via RHCL:

- `hostname` deve ser obrigatorio
- alternativamente, o assistente deve resolver o FQDN via `dns_suffix`
- `create_httproute` nao deve aceitar rota externa sem `hostname`
- `expose_service` deve ser a tool preferida

### Caso 2 - erro cita o usuário real

Exemplo:

```text
User "alice" cannot create resource "httproutes"
```

Isso significa que o passthrough está funcionando e o problema agora é RBAC
do usuário, não do servidor.

### Caso 3 - `Empty reply from server`

Se acontecer durante `curl`, verifique:

1. se o `port-forward` ainda está preso ao pod atual
2. se houve restart do pod no meio do teste
3. se vale portar diretamente para o pod em vez do service

## Falha de rollout

Se o deployment ficar preso, verificar:

```bash
oc -n ols-mcp-server describe deployment rhcl-mcp-server
oc -n ols-mcp-server get events --sort-by=.lastTimestamp | tail -n 30
```

Durante a validação desta correção apareceu, intermitentemente:

```text
admission plugin "MutatingAdmissionWebhook" failed to complete mutation in 13s
```

Quando isso acontecer, o problema é de admissão do cluster e não do código
do MCP server.
