# Operando o RHCL via Lightspeed e MCP Server

Este documento descreve como o OpenShift Lightspeed pode ajudar a operar
o Red Hat Connectivity Link usando o MCP Server integrado.

## Como funciona

O OpenShift Lightspeed tem acesso a um MCP Server que consegue executar
comandos no cluster OpenShift usando as permissões do usuário logado.

O MCP Server suporta **qualquer recurso Kubernetes**, incluindo CRDs como:
- `gateway.networking.k8s.io/v1` - Gateway, HTTPRoute, GRPCRoute
- `kuadrant.io/v1` - AuthPolicy, RateLimitPolicy, DNSPolicy, TLSPolicy

Operacoes de escrita devem respeitar o RBAC do usuario logado. Se a resposta
do Lightspeed mencionar a service account do pod (`system:serviceaccount:...`)
em vez do usuario real, isso indica problema no passthrough do token para o
MCP customizado.

## Regras operacionais para expor aplicacoes

Quando o usuario pedir para expor, publicar ou colocar uma API no ar via RHCL,
o comportamento esperado e autonomo:

1. garantir uma `HTTPRoute` com `hostname`
2. garantir uma `DNSPolicy` no `Gateway` se ainda nao existir
3. responder com o FQDN final e com o que foi alterado

Regras importantes:

- nunca criar `HTTPRoute` externa sem `hostnames`
- para exposicao externa, o `hostname` e obrigatorio
- se o usuario nao fornecer FQDN, gerar a partir de `<service>.<dns_suffix>` quando o sufixo do ambiente for conhecido
- `DNSPolicy` e ligada ao `Gateway`, nao a `HTTPRoute`
- se ja existir `DNSPolicy` para o `Gateway`, reutilizar
- preferir uma acao unica que deixe a API funcionando, em vez de apenas gerar YAML

### Ferramenta preferida

Ao expor um servico, prefira a tool:

- `expose_service`

Ela deve:

- criar ou atualizar a `HTTPRoute`
- incluir o `hostname` ou gera-lo a partir de `dns_suffix`
- garantir `DNSPolicy` no `Gateway` quando necessario
- retornar o hostname final

## Exemplos de prompts que funcionam

### Listar recursos do RHCL

```
"List all Gateways in the cluster"
"Show me all HTTPRoutes"
"List AuthPolicies across all namespaces"
"What DNSPolicies exist?"
"Show TLSPolicies in openshift-ingress namespace"
"List RateLimitPolicies"
```

### Diagnosticar um Gateway

```
"Show the status of the rhcl-apps-gateway Gateway"
"Check if the Gateway is programmed"
"What's the ELB address for the gateway?"
"List all routes bound to rhcl-apps-gateway"
```

### Expor uma aplicacao via RHCL

```
"Expose the rhcl-lab service via the rhcl-apps-gateway at rhcl-lab.poc.rhcl.com.br"
"Publish the debugocp service in debugocp3 at debugocp.poc.rhcl.com.br"
"Make my API reachable via RHCL and ensure DNS is published automatically"
"Create an AuthPolicy to allow access to my HTTPRoute"
"Configure TLS for my HTTPRoute"
```

### Verificar conectividade

```
"Check if the gateway has an ELB and is accepting traffic"
"List all pods in the tests namespace"
"Check the service my-app in tests namespace"
```

## Recursos e seus grupos de API

| Recurso | Grupo API | Versao |
|---|---|---|
| Gateway | gateway.networking.k8s.io | v1 |
| HTTPRoute | gateway.networking.k8s.io | v1 |
| GRPCRoute | gateway.networking.k8s.io | v1 |
| AuthPolicy | kuadrant.io | v1 |
| RateLimitPolicy | kuadrant.io | v1 |
| DNSPolicy | kuadrant.io | v1 |
| TLSPolicy | kuadrant.io | v1 |

## Comandos uteis (MCP)

Quando perguntar ao Lightspeed, use linguagem natural:

- "List all Gateways" → MCP executa `oc get gateway -A`
- "Show HTTPRoutes in tests namespace" → `oc get httproute -n tests`
- "Describe the Gateway" → `oc describe gateway rhcl-apps-gateway -n openshift-ingress`
- "Expose service via RHCL" → MCP deve preferir `expose_service`
- "Create HTTPRoute" → use so quando o usuario pedir controle detalhado da rota
- "Ensure DNS publication" → MCP deve conferir ou criar `DNSPolicy` no Gateway
