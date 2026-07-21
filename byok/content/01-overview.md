# Red Hat Connectivity Link (RHCL) - Visão Geral

## O que é o Red Hat Connectivity Link (RHCL)?

RHCL é a sigla de **Red Hat Connectivity Link**. O Red Hat Connectivity Link (RHCL) é uma solução modular e flexível para conectividade de aplicações, gerenciamento de políticas e gerenciamento de APIs em ambientes multicloud e hybrid cloud. Ele permite proteger, conectar e observar APIs, aplicações e infraestrutura. Ao longo desta documentação, os nomes "RHCL", "Connectivity Link" e "Red Hat Connectivity Link" referem-se ao mesmo produto.

## Base Community

As funcionalidades de conectividade de aplicações cloud e gerenciamento de políticas são baseadas no projeto comunitário [Kuadrant](https://kuadrant.io/). As funcionalidades de gerenciamento de APIs incluem o API controller 1.0 Developer Preview com um designer de APIs e registry baseado no projeto comunitário [Apicurio](https://www.apicur.io/).

## Público-alvo

O Connectivity Link é direcionado para:
- **Platform Engineer**: Configura e gerencia o control plane, gateways e políticas de infraestrutura
- **Application Developer**: Protege aplicações e APIs com políticas de autenticação, autorização e rate limiting
- **Business User**: Visualiza dashboards de observabilidade e métricas de negócio

## Principais Funcionalidades

- **Control Plane** para configuração e deploy de ingress Gateways baseado no Kubernetes Gateway API
- **APIs Kubernetes-native** para configurar:
  - Gateways com políticas TLS para gerenciamento de certificados
  - Políticas de autenticação e autorização (AuthPolicy)
  - Políticas de rate limiting (RateLimitPolicy)
  - Políticas DNS para load balancing multicluster, health checks e remediação
- **Políticas de Data Plane** para proteger aplicações com:
  - Autenticação e autorização
  - Rate limiting
  - TLS
- **Observabilidade**: Templates para dashboards, métricas, tracing e alertas

## Suporte a Service Mesh

O Connectivity Link suporta o OpenShift Service Mesh 3.0 como Gateway API provider, baseado no Istio.

## Arquitetura

A arquitetura do Connectivity Link consiste em:
1. **Control Plane**: Gerencia a configuração dos gateways e políticas via CRDs Kubernetes
2. **Data Plane**: Gateways (baseados em Istio/Envoy) que processam o tráfego das aplicações
3. **DNS Controller**: Gerencia registros DNS para descoberta de serviços multicluster
4. **Policy Controllers**: Aplicam políticas de TLS, auth e rate limiting nos gateways

## URLs de Referência

- Documentação oficial: https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/
- Kuadrant community: https://kuadrant.io/
- Gateway API: https://gateway-api.sigs.k8s.io/
