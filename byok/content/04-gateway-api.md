# Gateway API no Red Hat Connectivity Link

## Visão Geral

O Connectivity Link usa o Kubernetes Gateway API como padrão para configurar ingress gateways. Gateway API é um padrão do CNCF que substitui o Ingress tradicional com recursos mais expressivos e extensíveis.

## Conceitos Gateway API

### GatewayClass
Recurso cluster-scoped que define um tipo de gateway. Exemplo: `istio`, `nginx`.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: istio
spec:
  controllerName: istio.io/gateway-controller
```

### Gateway
Define o ponto de entrada de tráfego.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-gateway
  namespace: my-app
spec:
  gatewayClassName: istio
  listeners:
    - name: https
      port: 443
      protocol: HTTPS
      hostname: "*.example.com"
      tls:
        mode: Terminate
        certificateRefs:
          - name: my-cert
```

### HTTPRoute
Define regras de roteamento para tráfego HTTP/HTTPS.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-route
  namespace: my-app
spec:
  parentRefs:
    - name: my-gateway
  hostnames:
    - "api.example.com"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /v1
      backendRefs:
        - name: my-service
          port: 8080
```

## Políticas Gateway API no Connectivity Link

### TLSPolicy - Gerenciamento de Certificados

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: TLSPolicy
metadata:
  name: my-tls-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  issuerRef:
    group: cert-manager.io
    kind: Issuer
    name: letsencrypt-prod
```

### AuthPolicy - Autenticação e Autorização

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: AuthPolicy
metadata:
  name: my-auth-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: my-route
  rules:
    authentication:
      jwt:
        issuers:
          - issuer: https://auth.example.com
            jwksUrl: https://auth.example.com/.well-known/jwks.json
```

### RateLimitPolicy - Rate Limiting

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: RateLimitPolicy
metadata:
  name: my-rate-limit
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: my-route
  limits:
    my-limit:
      rates:
        - limit: 100
          window: 60
          unit: second
      counters:
        - request.path
```

### DNSPolicy - DNS Multicluster

```yaml
apiVersion: kuadrant.io/v1alpha1
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
  loadBalancing:
    geo: weighted
    defaultGeo: us-east
```

## Boas Práticas

1. Sempre use HTTPS com certificados TLS
2. Configure rate limiting para proteger seus backends
3. Use autenticação JWT para APIs expostas externamente
4. Configure health checks no DNSPolicy para remediação automática
5. Separe gateways por ambiente (dev, staging, prod)
