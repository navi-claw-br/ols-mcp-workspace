# Gateway API in Red Hat Connectivity Link (RHCL)

## Overview

Connectivity Link uses the Kubernetes Gateway API as the standard for configuring ingress gateways. Gateway API is a CNCF standard that replaces the traditional Ingress with more expressive and extensible resources.

## Gateway API Concepts

### GatewayClass
Cluster-scoped resource that defines a type of gateway. Example: `istio`, `nginx`.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: istio
spec:
  controllerName: istio.io/gateway-controller
```

### Gateway
Defines the traffic entry point.

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
Defines routing rules for HTTP/HTTPS traffic.

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

For external exposure via RHCL:

- `hostnames` must not be empty
- the route must point to a valid `Gateway`
- the hostname must be an FQDN that the team wants to publish

## Gateway API Policies in Connectivity Link

### TLSPolicy - Certificate Management

```yaml
apiVersion: kuadrant.io/v1
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

### AuthPolicy - Authentication and Authorization

```yaml
apiVersion: kuadrant.io/v1
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
apiVersion: kuadrant.io/v1
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

### DNSPolicy - Multicluster DNS

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
  loadBalancing:
    geo: weighted
    defaultGeo: us-east
```

Important:

- `DNSPolicy` is attached to the `Gateway`
- the published FQDNs come from the `hostnames` of the `HTTPRoutes` attached to that `Gateway`
- if there is no `hostname` on the `HTTPRoute`, there is no specific FQDN to publish

## Best Practices

1. Always use HTTPS with TLS certificates
2. Configure rate limiting to protect your backends
3. Use JWT authentication for externally exposed APIs
4. Configure health checks in the DNSPolicy for automatic remediation
5. Separate gateways per environment (dev, staging, prod)
6. When exposing an API, make sure there is a `hostname` on the `HTTPRoute` and a `DNSPolicy` on the `Gateway`
