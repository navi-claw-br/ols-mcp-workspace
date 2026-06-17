# Instalação do Red Hat Connectivity Link

## Pré-requisitos

- Cluster OpenShift 4.14+
- OpenShift Service Mesh 3.0 instalado
- Cert-manager Operator instalado (para TLS automático)
- Acesso cluster-admin
- OpenShift CLI (oc)

## Instalação via OperatorHub

### 1. Instalar o OpenShift Service Mesh 3.0

```bash
# Criar namespace
oc new project istio-system

# Instalar o Service Mesh Control Plane
cat <<EOF | oc apply -f -
apiVersion: sailoperator.io/v1
kind: Istio
metadata:
  name: default
spec:
  namespace: istio-system
  version: v1.22.0
  values:
    meshConfig:
      accessLogFile: /dev/stdout
EOF
```

### 2. Instalar o Cert Manager

```bash
# Instalar via OperatorHub
oc apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml
```

### 3. Instalar o Connectivity Link Operator

```bash
# Criar namespace
oc new-project connectivity-link-system

# Instalar o operator via subscription
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: connectivity-link-operator
  namespace: connectivity-link-system
spec:
  channel: stable
  name: connectivity-link-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

### 4. Criar a instância do Connectivity Link

```bash
cat <<EOF | oc apply -f -
apiVersion: kuadrant.io/v1beta1
kind: Kuadrant
metadata:
  name: kuadrant
spec:
  serviceMesh:
    istioControlPlane:
      name: default
      namespace: istio-system
EOF
```

## Verificação da Instalação

```bash
# Verificar pods
oc get pods -n connectivity-link-system
oc get pods -n istio-system

# Verificar CRDs
oc get crd | grep kuadrant
oc get crd | grep gateway.networking

# Verificar gateways
oc get gateway -A
```

## Recursos Importantes

- Documentação de instalação: https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/
- Kuadrant operator: https://github.com/kuadrant/kuadrant-operator
- System requirements: OpenShift 4.14+, 16GB RAM por nó (recomendado)
