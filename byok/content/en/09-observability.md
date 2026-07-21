# Observability in Red Hat Connectivity Link (RHCL)

## Overview

Connectivity Link provides ready-to-use observability templates including Grafana dashboards, Prometheus metrics, distributed tracing, and alerts.

## Metrics

### Gateway Metrics (Envoy)

Metrics exposed by Envoy on the gateways:

| Metric | Description |
|---------|-----------|
| `envoy_cluster_upstream_rq_total` | Total requests to upstream |
| `envoy_cluster_upstream_rq_xx` | Requests by response code (2xx, 3xx, 4xx, 5xx) |
| `envoy_cluster_upstream_rq_time` | Request response time |
| `envoy_cluster_upstream_cx_active` | Active connections |
| `envoy_http_downstream_rq_time` | Downstream response time |

### Rate Limiting Metrics

| Metric | Description |
|---------|-----------|
| `limitador_requests_total` | Total requests processed |
| `limitador_ratelimited_total` | Rate-limited requests (HTTP 429) |
| `limitador_cache_hits_total` | Rate limiter cache hits |
| `limitador_cache_misses_total` | Rate limiter cache misses |

### DNS Controller Metrics

| Metric | Description |
|---------|-----------|
| `dns_health_check_total` | Total health checks executed |
| `dns_health_check_failures` | Failed health checks |
| `dns_record_provisioned` | Provisioned DNS records |

## Grafana Dashboards

Connectivity Link offers pre-configured dashboards:

1. **Connectivity Link Overview** - System overview
2. **Gateway Traffic** - Traffic on the gateways
3. **Rate Limiting** - Rate limiting statistics
4. **DNS Health** - DNS endpoint health
5. **Auth Metrics** - Authentication metrics

Enabling the dashboards:

```bash
# Configurar dashboards
oc apply -f https://raw.githubusercontent.com/kuadrant/kuadrant-operator/main/config/observability/grafana-dashboards.yaml
```

## Distributed Tracing

Tracing uses OpenTelemetry to trace requests across the components:

```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: tracing
  namespace: istio-system
spec:
  tracing:
    - providers:
        - name: otel-collector
      randomSamplingPercentage: 10.0
```

## Alerts

Pre-configured Prometheus alerts:

| Alert | Condition | Severity |
|--------|----------|------------|
| `GatewayDown` | Gateway not ready > 5min | critical |
| `HighErrorRate` | Error rate > 5% over 5min | warning |
| `RateLimitExceeded` | Too many rate-limited requests | info |
| `CertificateExpiring` | TLS certificate expires in < 30 days | warning |
| `DNSHealthCheckFailing` | DNS health check failing | critical |

```bash
# Verificar alertas
oc get prometheusrule -A

# Verificar targets do Prometheus
oc get servicemonitor -A
```

## Logs

Component log structure:

```bash
# Logs do gateway (Envoy)
oc logs -l gateway.networking.k8s.io/gateway-name=my-gateway -n istio-system

# Logs do rate limiter
oc logs -l app=limitador -n connectivity-link-system

# Logs do DNS controller
oc logs -l app=kuadrant-dns-controller -n connectivity-link-system

# Logs do auth controller
oc logs -l app=kuadrant-controller -n connectivity-link-system
```
