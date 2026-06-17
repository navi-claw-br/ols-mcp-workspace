# Políticas TLS no Red Hat Connectivity Link

## TLSPolicy

A TLSPolicy gerencia certificados TLS para os gateways, automatizando a emissão, renovação e configuração de certificados.

## Tipos de Certificado Suportados

### 1. Certificados Customizados (manual)

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

### 2. Certificados Automáticos via ACME (Let's Encrypt)

Pré-requisito: cert-manager Operator instalado.

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

## Configuração TLS no Gateway

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

## Modos TLS

- **Terminate**: O gateway termina o TLS e encaminha tráfego HTTP para o backend
- **Passthrough**: O gateway encaminha o tráfego TLS sem terminar (para backends que precisam de TLS)
- **Mutual**: mTLS - cliente e servidor se autenticam mutuamente

## Verificação

```bash
# Verificar certificados
oc get certificate -A

# Verificar se o gateway esta pronto
oc get gateway <nome> -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'

# Testar conexao TLS
curl -vI https://api.example.com
```
