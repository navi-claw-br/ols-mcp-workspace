# DNS and Multicluster in Red Hat Connectivity Link (RHCL)

## DNSPolicy

The DNSPolicy manages DNS records for gateway exposure, with support for health checks, multicluster load balancing, and automatic remediation.

In the RHCL flow:

- the `HTTPRoute` defines the `hostname`
- the `DNSPolicy` publishes to DNS the hostnames of the routes attached to the `Gateway`
- therefore, exposing a service externally requires both sides

## Basic Configuration

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
    protocol: HTTP
    failureThreshold: 3
    successThreshold: 1
```

## Supported DNS Providers

### AWS Route53
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-route53-credentials
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: <key>
  AWS_SECRET_ACCESS_KEY: <secret>
---
apiVersion: kuadrant.io/v1
kind: ManagedZone
metadata:
  name: example-com
spec:
  domain: example.com
  dnsProvider:
    type: aws-route53
    credentials:
      secretRef:
        name: aws-route53-credentials
```

### Azure DNS
```yaml
apiVersion: kuadrant.io/v1
kind: ManagedZone
metadata:
  name: example-com
spec:
  domain: example.com
  dnsProvider:
    type: azure-dns
    credentials:
      secretRef:
        name: azure-dns-credentials
```

### Google Cloud DNS
```yaml
apiVersion: kuadrant.io/v1
kind: ManagedZone
metadata:
  name: example-com
spec:
  domain: example.com
  dnsProvider:
    type: google-cloud-dns
    credentials:
      secretRef:
        name: gcp-dns-credentials
```

## Advanced Health Checks

```yaml
apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: advanced-health-check
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: multi-region-gateway
  healthCheck:
    path: /healthz
    port: 8080
    protocol: HTTPS
    failureThreshold: 3
    successThreshold: 2
    interval: 10s
    timeout: 5s
  loadBalancing:
    geo: weighted
    defaultGeo: us-east
    weights:
      us-east: 70
      eu-west: 30
```

## Multicluster with GeoDNS

Connectivity Link supports multicluster deployments where gateways in different regions/clouds are discovered via DNS.

### Multicluster Architecture

```
                    +--> us-east-1 cluster (70%)
                    |
Usuario -> DNS ---->+
                    |
                    +--> eu-west-1 cluster (30%)
```

### Multicluster Configuration

```yaml
# Cluster 1: us-east-1
apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: us-east-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  loadBalancing:
    geo: weighted
    defaultGeo: us-east
    weights:
      us-east: 70

# Cluster 2: eu-west-1
---
apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: eu-west-policy
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: my-gateway
  loadBalancing:
    geo: weighted
    defaultGeo: eu-west
    weights:
      eu-west: 30
```

## Automatic Remediation

When a health check fails, the DNS controller automatically:
1. Removes the unhealthy endpoint from DNS
2. Redirects traffic to healthy endpoints
3. Re-adds the endpoint once it recovers

## Practical Rule for Lightspeed

If the user asks to expose an API and provides an FQDN, the assistant must:

1. ensure `hostnames` on the `HTTPRoute`
2. check whether a `DNSPolicy` already exists for the `Gateway`
3. create the `DNSPolicy` if it does not exist
4. respond with the final hostname, not with a manifest for the user to apply

```bash
# Verificar health checks
oc get dnshealthcheck -A

# Verificar endpoints DNS
oc get dnsrecord -A

# Verificar ManagedZone
oc get managedzone -A
```
