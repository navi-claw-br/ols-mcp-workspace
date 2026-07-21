# Authentication and Authorization Policies (AuthPolicy) in Red Hat Connectivity Link (RHCL)

## Overview

The AuthPolicy allows you to configure authentication and authorization for requests arriving at gateways managed by Connectivity Link.

## Supported Authentication Providers

### 1. JWT / OIDC

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: AuthPolicy
metadata:
  name: jwt-auth
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: secured-route
  rules:
    authentication:
      jwt:
        - name: keycloak
          issuerUrl: https://auth.example.com/realms/myrealm
        - name: custom-jwt
          issuer: https://custom-idp.example.com
          jwksUrl: https://custom-idp.example.com/.well-known/jwks.json
          tokenLocations:
            - in: header
              name: Authorization
              valuePrefix: "Bearer "
```

### 2. API Key

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: AuthPolicy
metadata:
  name: apikey-auth
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api-route
  rules:
    authentication:
      apiKey:
        - name: my-api-key
          credentials:
            - in: header
              key: X-API-Key
          allCredentials: true
```

### 3. Multiple Providers

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: AuthPolicy
metadata:
  name: multi-auth
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: my-route
  rules:
    authentication:
      jwt:
        - name: keycloak
          issuerUrl: https://auth.example.com/realms/myrealm
      apiKey:
        - name: api-key
          credentials:
            - in: header
              key: X-API-Key
    authorization:
      jwt:
        - name: keycloak
          requiredClaims:
            - key: realm_access.roles
              value: admin
```

## Claims-Based Authorization

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: AuthPolicy
metadata:
  name: claims-auth
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: admin-route
  rules:
    authentication:
      jwt:
        - name: oidc-provider
          issuerUrl: https://auth.example.com
    authorization:
      jwt:
        - name: oidc-provider
          requiredClaims:
            - key: email
              value: "@example.com"
            - key: roles
              value: "admin"
```

## Usage Patterns

### Public Route + Protected Route

```yaml
# Rota pública
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: public-route
spec:
  parentRefs:
    - name: my-gateway
  hostnames:
    - "public.example.com"
  rules:
    - backendRefs:
        - name: public-service
          port: 8080

# Rota protegida (AuthPolicy referencia esta rota)
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: secured-route
spec:
  parentRefs:
    - name: my-gateway
  hostnames:
    - "api.example.com"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: secured-service
          port: 8080
```

## Debugging and Troubleshooting

```bash
# Verificar status da AuthPolicy
oc get authpolicy -A

# Ver logs do gateway
oc logs -l gateway.networking.k8s.io/gateway-name=my-gateway -n istio-system

# Testar rota sem auth (deve retornar 401)
curl -v https://api.example.com/api/data

# Testar rota com token valido
curl -v -H "Authorization: Bearer <token>" https://api.example.com/api/data
```
