# Observabilidade no Red Hat Connectivity Link

## Visão Geral

O Connectivity Link fornece templates prontos para observabilidade incluindo dashboards Grafana, métricas Prometheus, tracing distribuído e alertas.

## Métricas

### Métricas do Gateway (Envoy)

Métricas expostas pelo Envoy nos gateways:

| Métrica | Descrição |
|---------|-----------|
| `envoy_cluster_upstream_rq_total` | Total de requisições para upstream |
| `envoy_cluster_upstream_rq_xx` | Requisições por código de resposta (2xx, 3xx, 4xx, 5xx) |
| `envoy_cluster_upstream_rq_time` | Tempo de resposta das requisições |
| `envoy_cluster_upstream_cx_active` | Conexões ativas |
| `envoy_http_downstream_rq_time` | Tempo de resposta downstream |

### Métricas do Rate Limiting

| Métrica | Descrição |
|---------|-----------|
| `limitador_requests_total` | Total de requisições processadas |
| `limitador_ratelimited_total` | Requisições rate limited (HTTP 429) |
| `limitador_cache_hits_total` | Cache hits do rate limiter |
| `limitador_cache_misses_total` | Cache misses do rate limiter |

### Métricas do DNS Controller

| Métrica | Descrição |
|---------|-----------|
| `dns_health_check_total` | Total de health checks executados |
| `dns_health_check_failures` | Health checks com falha |
| `dns_record_provisioned` | Registros DNS provisionados |

## Dashboards Grafana

O Connectivity Link oferece dashboards pré-configurados:

1. **Connectivity Link Overview** - Visão geral do sistema
2. **Gateway Traffic** - Tráfego nos gateways
3. **Rate Limiting** - Estatísticas de rate limiting
4. **DNS Health** - Saúde dos endpoints DNS
5. **Auth Metrics** - Métricas de autenticação

Ativação dos dashboards:

```bash
# Configurar dashboards
oc apply -f https://raw.githubusercontent.com/kuadrant/kuadrant-operator/main/config/observability/grafana-dashboards.yaml
```

## Tracing Distribuído

O tracing usa OpenTelemetry para rastrear requisições através dos componentes:

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

## Alertas

Alertas Prometheus pré-configurados:

| Alerta | Condição | Severidade |
|--------|----------|------------|
| `GatewayDown` | Gateway não está pronto > 5min | critical |
| `HighErrorRate` | Taxa de erro > 5% em 5min | warning |
| `RateLimitExceeded` | Muitas requisições rate limited | info |
| `CertificateExpiring` | Certificado TLS expira em < 30 dias | warning |
| `DNSHealthCheckFailing` | Health check DNS falhando | critical |

```bash
# Verificar alertas
oc get prometheusrule -A

# Verificar targets do Prometheus
oc get servicemonitor -A
```

## Logs

Estrutura de logs dos componentes:

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
