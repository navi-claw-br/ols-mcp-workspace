# Rate Limiting no Red Hat Connectivity Link

## Visão Geral

Rate limiting protege suas APIs e aplicações controlando a taxa de requisições que cada cliente pode fazer. O Connectivity Link suporta rate limiting via RateLimitPolicy.

## Tipos de Rate Limiting

### 1. Rate Limiting por IP

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

### 2. Rate Limiting por Usuário (JWT Claims)

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

### 3. Rate Limiting por Caminho

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

### 4. Múltiplas Camadas de Rate Limit

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

## Estratégias de Limitação

### Window Types (Janelas)
- **second**: Limitação por segundo (alta granularidade)
- **minute**: Limitação por minuto
- **hour**: Limitação por hora (para cotas generosas)

### Comportamento
- **Synchronous**: Cliente recebe 429 Too Many Requests imediatamente
- **Headers de resposta**:
  - `X-RateLimit-Limit`: Limite configurado
  - `X-RateLimit-Remaining`: Requisições restantes na janela
  - `X-RateLimit-Reset`: Timestamp de reset da janela

## Exemplo Completo

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
