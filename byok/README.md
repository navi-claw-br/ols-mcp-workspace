# BYOK — Bring Your Own Knowledge para OpenShift Lightspeed

Este diretório contém tudo que você precisa para criar uma **imagem BYOK**
com documentação do **Red Hat Connectivity Link** e disponibilizá-la como
conhecimento customizado no OpenShift Lightspeed.

## Quick Start

```bash
# 1. Build da imagem BYOK
make build

# 2. Push para o registry do cluster
make push REGISTRY=default-route-openshift-image-registry.apps.<cluster>.com

# 3. (Opcional) Atualizar OLSConfig
make deploy

# OU tudo em um comando:
make all REGISTRY=<registry>
```

## O que é BYOK?

BYOK (Bring Your Own Knowledge) é uma funcionalidade (Technology Preview)
do OpenShift Lightspeed que permite adicionar sua própria documentação
como base de conhecimento para o LLM.

O fluxo é:

1. Escreva seus documentos em **Markdown**
2. **Construa uma imagem de container** com o Vector Database FAISS
3. **Publique** em um registry acessível pelo cluster
4. **Configure** o OLSConfig com `spec.ols.rag.image`

O Lightspeed Operator detecta a imagem, carrega o Vector DB e passa
a responder perguntas com base no seu conhecimento proprietário.

## Estrutura

```
byok/
├── README.md                  ← Você está aqui
├── Containerfile              ← Build da imagem BYOK (recomendado)
├── Makefile                   ← Targets: build, push, deploy, all
├── content/                   ← Documentos markdown do RHCL
│   ├── 01-overview.md
│   ├── 02-architecture.md
│   ├── 03-installation.md
│   ├── 04-gateway-api.md
│   ├── 05-tls-policies.md
│   ├── 06-auth-policies.md
│   ├── 07-rate-limiting.md
│   ├── 08-dns-multicluster.md
│   ├── 09-observability.md
│   └── 10-mcp-operations.md
├── scripts/
│   ├── build-byok.sh          ← Script wrapper (build + push)
│   ├── generate-vectordb.py   ← Gera FAISS index do markdown
│   ├── index-content.sh       ← Indexação via rag-content (legado)
│   ├── custom_processor.py    ← Metadata processor (legado)
│   └── requirements-build.txt ← Dependências Python do build
└── lightspeed-stack.yaml      ← Config Lightspeed Core (legado)
```

## Como Funciona

### Método 1: Build Direto (Containerfile) — Recomendado

Usa o `Containerfile` incluso que faz **multi-stage build**:

1. **Stage 1 (builder):** UBI9 + Python + sentence-transformers + FAISS
   - Lê os markdowns de `content/`
   - Chunk os documentos
   - Gera embeddings com `all-mpnet-base-v2`
   - Constrói índice FAISS
2. **Stage 2 (scratch):** Imagem mínima com apenas o Vector DB em `/rag/vector_db/`

```bash
# Via Makefile
make build

# Ou manualmente
podman build -t byok-rhcl:latest -f Containerfile .
```

### Método 2: lightspeed-rag-tool Oficial (Red Hat)

Usa a imagem oficial da Red Hat que faz todo o processo e gera a imagem
BYOK automaticamente via buildah interno.

```bash
# Login no registry.redhat.io
podman login registry.redhat.io

# Executar a tool
make tool-build

# Ou via script
./scripts/build-byok.sh --tool --push --registry quay.io/meuuser
```

**Requisitos:**
- Acesso ao `registry.redhat.io` (Red Hat SSO)
- `podman` instalado
- Dispositivo `/dev/fuse` disponível

## Push da Imagem

### Para o Registry Interno do OpenShift

```bash
# 1. Expor o registry (se ainda não estiver exposto)
oc patch configs.imageregistry.operator.openshift.io/cluster \
  --type merge -p '{"spec":{"defaultRoute":true}}'

# 2. Obter a URL do registry
REGISTRY_URL=$(oc get route default-route -n openshift-image-registry \
  --template='{{ .spec.host }}')

# 3. Login
podman login -u kubeadmin -p "$(oc whoami -t)" "$REGISTRY_URL"

# 4. Push
make push REGISTRY="$REGISTRY_URL" NAMESPACE=openshift-lightspeed
```

### Para Registry Externo (Quay, Docker Hub, etc.)

```bash
podman login quay.io
make push REGISTRY=quay.io/meuuser NAMESPACE=openshift-lightspeed

# Ou com tag específica
make push REGISTRY=quay.io/meuuser IMAGE_TAG=v1.0
```

## Configuração no OLSConfig

Após publicar a imagem, configure o OpenShift Lightspeed para usá-la:

```yaml
apiVersion: ols.openshift.io/v1alpha1
kind: OLSConfig
metadata:
  name: cluster
spec:
  llm:
    providers:
      - name: myOpenai
        type: openai
        credentialsSecretRef:
          name: openai-api-keys
        url: "https://api.openai.com/v1"
        models:
          - name: gpt-4o
  ols:
    defaultModel: gpt-4o
    defaultProvider: myOpenai
    rag:
      - image: image-registry.openshift-image-registry.svc:5000/openshift-lightspeed/byok-rhcl:latest
        indexID: vector_db_index
        indexPath: /rag/vector_db
```

Aplicar com:

```bash
oc apply -f olsconfig.yaml
# OU via patch:
make deploy
```

O Lightspeed Operator reinicia os pods do `lightspeed-app-server`.

## Verificação

```bash
# Verificar se os pods reiniciaram
oc get pods -n openshift-lightspeed -w

# Testar uma pergunta que use o conhecimento do Connectivity Link
# Pelo próprio console OpenShift, pergunte algo como:
# "Como configurar uma TLSPolicy no Red Hat Connectivity Link?"
```

## Personalização

### Adicionar Mais Conteúdo

```bash
# 1. Adicione arquivos .md em content/
cp minha-doc.md byok/content/

# 2. Reconstrua a imagem
make build

# 3. Push e deploy
make push deploy
```

### Usar Outro Modelo de Embedding

```bash
make build EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Nota:** A dimensão do embedding muda conforme o modelo. O `generate-vectordb.py`
detecta automaticamente a dimensão correta.

### Atualização Automática com Floating Tags

O OpenShift Lightspeed suporta atualização automática de imagens BYOK que
usam **floating tags** (ex: `latest`). Se a tag apontar para uma imagem
diferente, o Lightspeed detecta e atualiza o Vector DB automaticamente.

```yaml
rag:
  - image: registry.example.com/openshift-lightspeed/byok-rhcl:latest  # floating tag!
    indexID: vector_db_index
    indexPath: /rag/vector_db
```

## Troubleshooting

### OLSConfig não aceita o campo `rag`

Verifique se o OpenShift Lightspeed Operator é **1.0+** e se o campo
`rag` está na indentação correta (mesmo nível de `defaultModel`):

```yaml
spec:
  ols:              # ← nível spec.ols
    defaultModel: ...
    defaultProvider: ...
    rag:            # ← MESMO nível de defaultModel
      - image: ...
```

### Pods do Lightspeed não reiniciam

```bash
oc describe olsconfig cluster -n openshift-lightspeed
oc logs -n openshift-lightspeed -l app=lightspeed-operator
```

### Imagem não encontrada pelo cluster

Verifique se:

- O registry é acessível pelo cluster
- O `imagePullPolicy` padrão do OLS funciona com a tag usada
- A imagem existe no registry: `oc image info <pullspec>`

## Referências

- [Blog: Bring your own knowledge to OpenShift Lightspeed](https://www.redhat.com/en/blog/bring-your-own-knowledge-openshift-lightspeed)
- [Red Hat OpenShift Lightspeed 1.0 — Configure](https://docs.redhat.com/en/documentation/red_hat_openshift_lightspeed/1.0/html/configure/)
- [Red Hat Connectivity Link Documentation](https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/)
- [lightspeed-rag-content (GitHub)](https://github.com/openshift/lightspeed-rag-content)
