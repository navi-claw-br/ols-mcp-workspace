# TLS Policies in Red Hat Connectivity Link (RHCL)

## TLSPolicy

The TLSPolicy manages TLS certificates for the gateways, automating certificate issuance, renewal, and configuration.

## Supported Certificate Types

### 1. Custom Certificates (manual)

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: TLSPolicy
metadata:
  name: custom-cert-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  issuerRef:
    group: cert-manager.io
    kind: Issuer
    name: ca-issuer
```

### 2. Automatic Certificates via ACME (Let's Encrypt)

Prerequisite: cert-manager Operator installed.

```yaml
# ClusterIssuer para Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingressGateway:
            name: my-gateway
            namespace: my-app
```

```yaml
apiVersion: kuadrant.io/v1alpha1
kind: TLSPolicy
metadata:
  name: acme-tls-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  issuerRef:
    group: cert-manager.io
    kind: ClusterIssuer
    name: letsencrypt-prod
```

## TLS Configuration on the Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: secure-gateway
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
          - name: my-app-cert    # Gerenciado pela TLSPolicy
```

## TLS Modes

- **Terminate**: The gateway terminates TLS and forwards HTTP traffic to the backend
- **Passthrough**: The gateway forwards TLS traffic without terminating it (for backends that need TLS)
- **Mutual**: mTLS - client and server authenticate each other

## Verification

```bash
# Verificar certificados
oc get certificate -A

# Verificar se o gateway esta pronto
oc get gateway <nome> -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'

# Testar conexao TLS
curl -vI https://api.example.com
```
