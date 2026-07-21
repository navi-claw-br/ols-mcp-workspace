# Rate Limiting in Red Hat Connectivity Link (RHCL)

## Overview

Rate limiting protects your APIs and applications by controlling the request rate that each client can make. Connectivity Link supports rate limiting via RateLimitPolicy.

## Types of Rate Limiting

### 1. Rate Limiting by IP

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: RateLimitPolicy
metadata:
  name: ip-rate-limit
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: my-route
  limits:
    ip-limit:
      rates:
        - limit: 100
          window: 60
          unit: second
      counters:
        - source.ip
```

### 2. Rate Limiting by User (JWT Claims)

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: RateLimitPolicy
metadata:
  name: user-rate-limit
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: my-route
  limits:
    user-limit:
      rates:
        - limit: 1000
          window: 60
          unit: second
      counters:
        - auth.principal.username
```

### 3. Rate Limiting by Path

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: RateLimitPolicy
metadata:
  name: path-rate-limit
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: my-route
  limits:
    expensive-endpoint:
      rates:
        - limit: 10
          window: 60
          unit: second
      counters:
        - request.path
```

### 4. Multiple Rate Limit Tiers

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: RateLimitPolicy
metadata:
  name: multi-tier-rate-limit
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: my-route
  limits:
    global-per-user:
      rates:
        - limit: 1000
          window: 60
          unit: minute
      counters:
        - auth.principal.username
    per-endpoint:
      rates:
        - limit: 100
          window: 60
          unit: second
      counters:
        - request.path
```

## Limiting Strategies

### Window Types
- **second**: Per-second limiting (high granularity)
- **minute**: Per-minute limiting
- **hour**: Per-hour limiting (for generous quotas)

### Behavior
- **Synchronous**: The client receives 429 Too Many Requests immediately
- **Response headers**:
  - `X-RateLimit-Limit`: Configured limit
  - `X-RateLimit-Remaining`: Requests remaining in the window
  - `X-RateLimit-Reset`: Window reset timestamp

## Complete Example

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-route
spec:
  parentRefs:
    - name: my-gateway
  hostnames:
    - "api.example.com"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api/v1
      backendRefs:
        - name: api-service
          port: 8080
---
apiVersion: kuadrant.io/v1alpha1
kind: RateLimitPolicy
metadata:
  name: api-rate-limit
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api-route
  limits:
    free-tier:
      rates:
        - limit: 10
          window: 60
          unit: second
      counters:
        - source.ip
```

## Troubleshooting

```bash
# Verificar RateLimitPolicy
oc get ratelimitpolicy -A

# Verificar se o rate limit esta ativo
curl -v https://api.example.com/api/v1/status
# Response headers devem incluir X-RateLimit-*

# Logs do rate limit service
oc logs -l app=limitador -n connectivity-link-system

# Testar rate limit com muitas requisicoes
for i in $(seq 1 20); do curl -s -o /dev/null -w "%{http_code}\n" https://api.example.com/api/v1/status; done
```
