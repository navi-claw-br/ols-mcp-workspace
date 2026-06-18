# Operando o RHCL via Lightspeed e MCP Server

Este documento descreve como o OpenShift Lightspeed pode ajudar a operar
o Red Hat Connectivity Link usando o MCP Server integrado.

## Como funciona

O OpenShift Lightspeed tem acesso a um MCP Server que consegue executar
comandos no cluster OpenShift usando as permissões do usuário logado.

O MCP Server suporta **qualquer recurso Kubernetes**, incluindo CRDs como:
- `gateway.networking.k8s.io/v1` - Gateway, HTTPRoute, GRPCRoute
- `kuadrant.io/v1` - AuthPolicy, RateLimitPolicy, DNSPolicy, TLSPolicy

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
"Create an HTTPRoute for my-app pointing to my-app service on port 8080"
"Expose the rhcl-lab service via the rhcl-apps-gateway"
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
- "Create HTTPRoute" → MCP cria via YAML/JSON
