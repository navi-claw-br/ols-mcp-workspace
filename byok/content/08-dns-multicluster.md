# DNS e Multicluster no Red Hat Connectivity Link

## DNSPolicy

A DNSPolicy gerencia registros DNS para exposição de gateways, com suporte a health checks, load balancing multicluster e remediação automática.

No fluxo de RHCL:

- a `HTTPRoute` define o `hostname`
- a `DNSPolicy` publica no DNS os hostnames das rotas conectadas ao `Gateway`
- portanto, expor um servico externamente exige os dois lados

## Configuração Básica

```yaml
apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: my-dns-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  healthCheck:
    path: /healthz
    port: 8080
    protocol: HTTP
    failureThreshold: 3
    successThreshold: 1
```

## Provedores DNS Suportados

### AWS Route53
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-route53-credentials
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: <key>
  AWS_SECRET_ACCESS_KEY: <secret>
---
apiVersion: kuadrant.io/v1
kind: ManagedZone
metadata:
  name: example-com
spec:
  domain: example.com
  dnsProvider:
    type: aws-route53
    credentials:
      secretRef:
        name: aws-route53-credentials
```

### Azure DNS
```yaml
apiVersion: kuadrant.io/v1
kind: ManagedZone
metadata:
  name: example-com
spec:
  domain: example.com
  dnsProvider:
    type: azure-dns
    credentials:
      secretRef:
        name: azure-dns-credentials
```

### Google Cloud DNS
```yaml
apiVersion: kuadrant.io/v1
kind: ManagedZone
metadata:
  name: example-com
spec:
  domain: example.com
  dnsProvider:
    type: google-cloud-dns
    credentials:
      secretRef:
        name: gcp-dns-credentials
```

## Health Checks Avançados

```yaml
apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: advanced-health-check
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: multi-region-gateway
  healthCheck:
    path: /healthz
    port: 8080
    protocol: HTTPS
    failureThreshold: 3
    successThreshold: 2
    interval: 10s
    timeout: 5s
  loadBalancing:
    geo: weighted
    defaultGeo: us-east
    weights:
      us-east: 70
      eu-west: 30
```

## Multicluster com GeoDNS

O Connectivity Link suporta deploy multicluster onde gateways em diferentes regiões/clouds são descobertos via DNS.

### Arquitetura Multicluster

```
                    +--> us-east-1 cluster (70%)
                    |
Usuario -> DNS ---->+
                    |
                    +--> eu-west-1 cluster (30%)
```

### Configuração Multicluster

```yaml
# Cluster 1: us-east-1
apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: us-east-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  loadBalancing:
    geo: weighted
    defaultGeo: us-east
    weights:
      us-east: 70

# Cluster 2: eu-west-1
---
apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: eu-west-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  loadBalancing:
    geo: weighted
    defaultGeo: eu-west
    weights:
      eu-west: 30
```

## Remediação Automática

Quando um health check falha, o DNS controller automaticamente:
1. Remove o endpoint unhealthy do DNS
2. Redireciona tráfego para endpoints saudáveis
3. Re-adiciona o endpoint quando recuperar

## Regra pratica para o Lightspeed

Se o usuario pedir para expor uma API e fornecer um FQDN, o assistente deve:

1. garantir `hostnames` na `HTTPRoute`
2. conferir se ja existe `DNSPolicy` para o `Gateway`
3. criar a `DNSPolicy` se nao existir
4. responder com o hostname final, nao com um manifesto para o usuario aplicar

```bash
# Verificar health checks
oc get dnshealthcheck -A

# Verificar endpoints DNS
oc get dnsrecord -A

# Verificar ManagedZone
oc get managedzone -A
```
