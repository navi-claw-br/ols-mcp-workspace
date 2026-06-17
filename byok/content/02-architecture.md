# Arquitetura do Red Hat Connectivity Link

## Componentes Principais

O Connectivity Link é composto pelos seguintes componentes:

### 1. Gateway API Controller

Gerencia a configuração de ingress gateways usando o padrão Kubernetes Gateway API.

Recursos Gateway API suportados:
- `Gateway` - Define o listener e configurações do gateway
- `HTTPRoute` - Roteamento de tráfego HTTP/HTTPS
- `TLSRoute` - Roteamento de tráfego TLS
- `TCPRoute` - Roteamento de tráfego TCP
- `UDPRoute` - Roteamento de tráfego UDP
- `GRPCRoute` - Roteamento de tráfego gRPC

### 2. Políticas (Policy CRDs)

O Connectivity Link estende o Gateway API com políticas customizadas:

**TLSPolicy**
- Gerencia certificados TLS para os gateways
- Suporte a证书 automático via Let's Encrypt / ACME
- Suporte a certificados customizados

**AuthPolicy**
- Autenticação de requisições
- Provedores suportados: OIDC, API Key, HTTP Basic
- Autorização baseada em claims JWT

**RateLimitPolicy**
- Rate limiting por:
  - IP de origem
  - Claims JWT (usuário, grupo)
  - Headers HTTP customizados
  - Caminho da requisição
- Limitação global ou por gateway

**DNSPolicy**
- Gerenciamento de registros DNS para health checks
- Load balancing multicluster com GeoDNS
- Health checks automatizados com remediação

### 3. DNS Controller

Responsável por:
- Publicar registros DNS baseados nos gateways configurados
- Health checks dos endpoints
- Remediação automática (remoção de endpoints unhealthy)
- Suporte a provedores: AWS Route53, Azure DNS, Google Cloud DNS

### 4. Observabilidade

Templates prontos para:
- Dashboards Grafana
- Métricas Prometheus
- Tracing distribuído
- Alertas configurados

## Fluxo de Tráfego

```
Cliente Externo
    |
    v
DNS (DNSPolicy - GeoDNS/Health Checks)
    |
    v
Gateway (Listener TLS - TLSPolicy)
    |
    v
HTTPRoute / Roteamento
    |
    v
AuthPolicy (Autenticação/Autorização)
    |
    v
RateLimitPolicy (Rate Limiting)
    |
    v
Backend (Aplicação no cluster)
```

## Modos de Deploy

O Connectivity Link pode ser instalado em diferentes topologias:

1. **Single-cluster**: Gateway e aplicações no mesmo cluster
2. **Multi-cluster**: Gateway em um cluster, aplicações distribuídas
3. **External DNS**: Gateway exposto com DNS gerenciado externamente
4. **Hub-Spoke**: Control plane centralizado, gateways em clusters remotos
