# MCP Server + BYOK para OpenShift Lightspeed

Integração do **OpenShift Lightspeed** com um **MCP Server** para executar comandos no OpenShift usando as permissões do usuário logado, mais **BYOK (Bring Your Own Knowledge)** sobre Red Hat Connectivity Link.

## Arquitetura

```
Usuário → OpenShift Console
  → OpenShift Lightspeed (OLS)
    → MCP Server (openshift-mcp-server)
      → OpenShift API (com token do usuário logado)
```

O Lightspeed atua como chat principal. Quando o LLM identifica que precisa executar um comando no cluster, ele chama as tools do MCP server configurado. O MCP server recebe o **token Bearer do usuário** (enviado pelo Lightspeed via `valueFrom.type: kubernetes`) e usa esse token para autenticar no OpenShift API.

### Fluxo de Autenticação

1. Usuário está logado no OpenShift Console com seu token OAuth
2. Lightspeed valida o token via `TokenReview` e `SubjectAccessReview`
3. Lightspeed encaminha o token para o MCP server via header `Authorization`
4. MCP server usa o token para fazer chamadas à API do OpenShift
5. RBAC do cluster determina o que o usuário pode ou não fazer

## Estrutura do Projeto

```
ols-mcp-workspace/
├── README.md                    # Este arquivo
├── mcp-server/                  # Deploy do MCP Server
│   ├── deploy.sh                # Script de deploy automatico
│   ├── values.yaml              # Valores Helm do openshift-mcp-server
│   ├── config.toml              # Configuracao do MCP server
│   └── rbac.yaml                # ClusterRole e bindings para users
├── rhcl-mcp-server/             # MCP customizado para RHCL/Kuadrant
│   ├── README.md                # Visao geral e validacao
│   ├── Dockerfile               # Build da imagem customizada
│   ├── deploy.sh                # Deploy/redeploy do servidor customizado
│   ├── deployment.yaml          # Deployment do servidor
│   ├── service.yaml             # Service do servidor
│   └── rhcl_server.py           # Implementacao das tools RHCL
├── ols-config/                  # Configuracao do OpenShift Lightspeed
│   ├── olsconfig.yaml           # OLSConfig CR com MCP servers
│   └── credentials-secret.yaml  # Secret para LLM provider
├── byok/                        # BYOK - Red Hat Connectivity Link
│   ├── content/                 # Documentacao markdown do Connectivity Link
│   │   ├── 01-overview.md
│   │   ├── 02-architecture.md
│   │   ├── 03-installation.md
│   │   ├── 04-gateway-api.md
│   │   ├── 05-tls-policies.md
│   │   ├── 06-auth-policies.md
│   │   ├── 07-rate-limiting.md
│   │   ├── 08-dns-multicluster.md
│   │   └── 09-observability.md
│   ├── scripts/
│   │   ├── index-content.sh     # Script para indexar com rag-content
│   │   └── custom_processor.py  # Metadata processor para documentos
│   └── lightspeed-stack.yaml    # Configuracao BYOK para Lightspeed Core
└── docs/
    ├── deploy-guide.md          # Guia de deploy completo
    ├── mcp-auth.md              # Detalhamento da autenticacao MCP
    ├── byok-guide.md            # Guia BYOK detalhado
    └── rhcl-mcp-server-runbook.md # Runbook do MCP customizado RHCL
```

## Pré-requisitos

- Cluster OpenShift 4.16+ com acesso `cluster-admin`
- [OpenShift Lightspeed Operator](https://docs.redhat.com/en/documentation/red_hat_openshift_lightspeed/1.0/html/install/) instalado
- `oc` e `helm` CLI
- LLM Provider (OpenAI, Vertex AI, RHEL AI, etc.) com credenciais
- (para BYOK) Lightspeed Core Service com suporte a BYOK

## Deploy Rápido

### 1. Credenciais do LLM

```bash
# Exemplo com OpenAI
oc create secret generic openai \
  --namespace openshift-lightspeed \
  --from-literal=apitoken="sk-..."
```

### 2. Deploy do MCP Server

```bash
cd mcp-server
./deploy.sh
```

### 3. Deploy do RHCL MCP Server

```bash
cd rhcl-mcp-server
./deploy.sh
```

### 4. Configurar Lightspeed

```bash
oc apply -f ols-config/olsconfig.yaml
```

### 5. Conceder Acesso aos Usuários

```bash
oc adm policy add-cluster-role-to-user ols-user <usuario>
oc adm policy add-cluster-role-to-user view <usuario>
oc adm policy add-cluster-role-to-user cluster-monitoring-view <usuario>
```

## Documentação importante

- `docs/deploy-guide.md` - deploy completo do stack
- `docs/mcp-auth.md` - autenticação e passthrough do token
- `docs/rhcl-mcp-server-runbook.md` - build, rollout, validação e troubleshooting do MCP RHCL
- `rhcl-mcp-server/README.md` - resumo operacional do servidor customizado

## Licença

Apache 2.0
