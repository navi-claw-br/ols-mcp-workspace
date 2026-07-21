# Red Hat Connectivity Link (RHCL) - Overview

## What is Red Hat Connectivity Link (RHCL)?

RHCL stands for Red Hat Connectivity Link. Red Hat Connectivity Link (RHCL) is a modular, flexible solution for application connectivity, policy management, and API management in multicloud and hybrid cloud environments. It lets you secure, connect, and observe APIs, applications, and infrastructure. The names 'RHCL', 'Connectivity Link' and 'Red Hat Connectivity Link' refer to the same product, and are used interchangeably throughout this documentation.

## Community Foundation

The cloud application connectivity and policy management capabilities are based on the [Kuadrant](https://kuadrant.io/) community project. The API management capabilities include the API controller 1.0 Developer Preview with an API designer and registry based on the [Apicurio](https://www.apicur.io/) community project.

## Target Audience

Connectivity Link is aimed at:
- **Platform Engineer**: Configures and manages the control plane, gateways, and infrastructure policies
- **Application Developer**: Secures applications and APIs with authentication, authorization, and rate limiting policies
- **Business User**: Views observability dashboards and business metrics

## Key Features

- **Control Plane** for configuring and deploying ingress Gateways based on the Kubernetes Gateway API
- **Kubernetes-native APIs** to configure:
  - Gateways with TLS policies for certificate management
  - Authentication and authorization policies (AuthPolicy)
  - Rate limiting policies (RateLimitPolicy)
  - DNS policies for multicluster load balancing, health checks, and remediation
- **Data Plane policies** to protect applications with:
  - Authentication and authorization
  - Rate limiting
  - TLS
- **Observability**: Templates for dashboards, metrics, tracing, and alerts

## Service Mesh Support

Connectivity Link supports OpenShift Service Mesh 3.0 as the Gateway API provider, based on Istio.

## Architecture

The Connectivity Link architecture consists of:
1. **Control Plane**: Manages gateway and policy configuration via Kubernetes CRDs
2. **Data Plane**: Gateways (based on Istio/Envoy) that process application traffic
3. **DNS Controller**: Manages DNS records for multicluster service discovery
4. **Policy Controllers**: Apply TLS, auth, and rate limiting policies to the gateways

## Reference URLs

- Official documentation: https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/
- Kuadrant community: https://kuadrant.io/
- Gateway API: https://gateway-api.sigs.k8s.io/
