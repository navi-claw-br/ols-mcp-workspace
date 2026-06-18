# RHCL MCP Server

Servidor MCP customizado para operar recursos do Red Hat Connectivity Link
via OpenShift Lightspeed, incluindo `Gateway`, `HTTPRoute`, `AuthPolicy`,
`RateLimitPolicy`, `DNSPolicy` e `TLSPolicy`.

## Arquivos

- `rhcl_server.py` - servidor MCP HTTP com tools RHCL
- `Dockerfile` - imagem do servidor
- `deployment.yaml` - Deployment OpenShift/Kubernetes
- `service.yaml` - Service interno do MCP
- `deploy.sh` - aplica manifests, atualiza a imagem e aguarda rollout

## Fluxo de autenticação

Este servidor depende de passthrough do token do usuário:

1. O Lightspeed chama o MCP com header `Authorization: Bearer <token>`
2. O servidor extrai esse token
3. As operações `oc get` e `oc create` precisam usar `--token <token>`
4. O RBAC efetivo deve ser o do usuário logado, nunca o da service account do pod

## Bug corrigido em 2026-06-18

O bug que causava erro de permissão em `create_httproute` era:

- `get/list` usavam o helper `get_oc_args(...)`
- `create` chamava `oc` direto, sem `--token`
- Resultado: a operação de escrita caía na service account do pod
  `system:serviceaccount:ols-mcp-server:ols-mcp-server`

O fix está em `oc_create_resource()`, que agora também usa `get_oc_args(args)`.

## Deploy rápido

```bash
podman build -t ghcr.io/navi-claw-br/rhcl-mcp-server:latest .
podman push ghcr.io/navi-claw-br/rhcl-mcp-server:latest
./deploy.sh
```

## Validação

Use o runbook completo:

- [docs/rhcl-mcp-server-runbook.md](../docs/rhcl-mcp-server-runbook.md)

Ele cobre:

- validação do `OLSConfig`
- port-forward no serviço/pod
- `tools/list`
- `tools/call` com `create_httproute`
- troubleshooting para diferenciar erro de passthrough vs. erro real de RBAC
