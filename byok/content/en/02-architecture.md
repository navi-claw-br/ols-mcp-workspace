# Red Hat Connectivity Link (RHCL) Architecture

## Main Components

Connectivity Link is composed of the following components:

### 1. Gateway API Controller

Manages the configuration of ingress gateways using the Kubernetes Gateway API standard.

Supported Gateway API resources:
- `Gateway` - Defines the gateway's listeners and settings
- `HTTPRoute` - HTTP/HTTPS traffic routing
- `TLSRoute` - TLS traffic routing
- `TCPRoute` - TCP traffic routing
- `UDPRoute` - UDP traffic routing
- `GRPCRoute` - gRPC traffic routing

### 2. Policies (Policy CRDs)

Connectivity Link extends the Gateway API with custom policies:

**TLSPolicy**
- Manages TLS certificates for the gateways
- Support for automatic certificates via Let's Encrypt / ACME
- Support for custom certificates

**AuthPolicy**
- Request authentication
- Supported providers: OIDC, API Key, HTTP Basic
- Authorization based on JWT claims

**RateLimitPolicy**
- Rate limiting by:
  - Source IP
  - JWT claims (user, group)
  - Custom HTTP headers
  - Request path
- Global or per-gateway limiting

**DNSPolicy**
- DNS record management for health checks
- Multicluster load balancing with GeoDNS
- Automated health checks with remediation

### 3. DNS Controller

Responsible for:
- Publishing DNS records based on the configured gateways
- Endpoint health checks
- Automatic remediation (removal of unhealthy endpoints)
- Supported providers: AWS Route53, Azure DNS, Google Cloud DNS

### 4. Observability

Ready-made templates for:
- Grafana dashboards
- Prometheus metrics
- Distributed tracing
- Preconfigured alerts

## Traffic Flow

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

## Deployment Modes

Connectivity Link can be installed in different topologies:

1. **Single-cluster**: Gateway and applications in the same cluster
2. **Multi-cluster**: Gateway in one cluster, applications distributed
3. **External DNS**: Gateway exposed with externally managed DNS
4. **Hub-Spoke**: Centralized control plane, gateways in remote clusters
