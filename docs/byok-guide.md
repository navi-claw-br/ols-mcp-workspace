# Guia BYOK — Build de Imagem para OpenShift Lightspeed

## Visão Geral

BYOK (Bring Your Own Knowledge) permite adicionar **conhecimento
customizado** ao OpenShift Lightspeed usando uma imagem de container
com um Vector Database FAISS.

Este guia cobre **dois métodos**:

1. **Build Direto (Containerfile)** — usando o `Containerfile` incluso
2. **Ferramenta Oficial Red Hat** — usando `lightspeed-rag-tool`

O conhecimento neste repositório é sobre **Red Hat Connectivity Link**
(configuração de Gateway API, TLS, Auth, Rate Limiting, DNS Multicluster,
Observabilidade).

## Arquitetura

```
[Documentos Markdown]
        ↓
[Gerar Embeddings + FAISS Index]
        ↓
[Imagem Container (/rag/vector_db)]
        ↓
[Registry Acessível pelo Cluster]
        ↓
[OLSConfig → spec.ols.rag.image]
        ↓
[Lightspeed Operator carrega Vector DB]
        ↓
[LLM consulta RAG com seu conhecimento]
```

O OpenShift Lightspeed suporta dois modos de RAG:

- **Automático:** contexto é injetado automaticamente antes de cada query
- **Tool RAG:** LLM pode buscar contexto sob demanda

## Pré-requisitos

- Cluster OpenShift 4.16+ com OpenShift Lightspeed 1.0+
- Container tool (`podman` ou `docker`)
- Acesso a um registry de container (interno do OCP ou externo)
- (Método oficial) Acesso ao `registry.redhat.io` e `podman` com `/dev/fuse`

## Método 1: Build Direto (Recomendado para este Repo)

Usa o `Containerfile` incluso que executa todo o pipeline de embedding
e indexação em multi-stage build.

### 1. Build

```bash
cd byok

# Via Makefile
make build

# Ou manualmente
podman build -t byok-rhcl:latest -f Containerfile .
```

O processo:
1. Instala dependências Python (sentence-transformers, FAISS)
2. Baixa o modelo de embedding `all-mpnet-base-v2` (~1.2GB)
3. Chunk os documentos markdown (1000 chars, overlap 200)
4. Gera embeddings e constrói índice FAISS
5. Empacota em imagem scratch em `/rag/vector_db/`

### 2. Push para Registry

```bash
# Registry interno do OCP
REGISTRY=$(oc get route default-route -n openshift-image-registry \
  --template='{{ .spec.host }}')

podman login -u kubeadmin -p "$(oc whoami -t)" "$REGISTRY"
make push REGISTRY="$REGISTRY"

# Ou registry externo
make push REGISTRY=quay.io/meuuser
```

### 3. Configurar OLSConfig

Adicione o bloco `rag` no OLSConfig:

```yaml
spec:
  ols:
    defaultModel: gpt-4o
    defaultProvider: myOpenai
    rag:
      - image: image-registry.openshift-image-registry.svc:5000/openshift-lightspeed/byok-rhcl:latest
        indexID: vector_db_index
        indexPath: /rag/vector_db
```

```bash
oc apply -f olsconfig.yaml
```

## Método 2: Ferramenta Oficial Red Hat

Usa a imagem `lightspeed-rag-tool-rhel9` do `registry.redhat.io`.

### 1. Login

```bash
podman login registry.redhat.io
# Use suas credenciais do Red Hat SSO
```

### 2. Executar a Tool

```bash
cd byok

# Via Makefile
make tool-build

# Ou manualmente
podman run -it --rm --device=/dev/fuse \
  -v $XDG_RUNTIME_DIR/containers/auth.json:/run/user/0/containers/auth.json:Z \
  -v ./content:/markdown:Z \
  -v ./vector_db/output:/output:Z \
  registry.redhat.io/openshift-lightspeed-tech-preview/lightspeed-rag-tool-rhel9:latest
```

### 3. Carregar e Publicar a Imagem

```bash
# Carregar a imagem gerada
podman load -i ./vector_db/output/byok-image.tar

# Taguear
podman tag localhost/byok-image:latest \
  default-route-openshift-image-registry.apps.<cluster>.com/openshift-lightspeed/byok-rhcl:latest

# Push
podman push default-route-openshift-image-registry.apps.<cluster>.com/openshift-lightspeed/byok-rhcl:latest
```

### 4. Configurar OLSConfig (idem Método 1)

## Script Automatizado

O script `byok/scripts/build-byok.sh` unifica ambos os métodos:

```bash
# Build direto + push
./scripts/build-byok.sh --push --registry quay.io/meuuser

# Build via tool oficial
./scripts/build-byok.sh --tool

# Build tool + push
./scripts/build-byok.sh --tool --push --registry quay.io/meuuser
```

## Verificação e Teste

### 1. Verificar se o Vector DB foi carregado

```bash
oc logs -n openshift-lightspeed deployment/lightspeed-app-server \
  | grep -i "rag\|byok\|vector"
```

### 2. Testar no Console OpenShift

Abra o Console → OpenShift Lightspeed → faça perguntas como:

- "O que é o Red Hat Connectivity Link?"
- "Como configurar uma TLSPolicy?"
- "Como criar um HTTPRoute com autenticação?"
- "Como configurar rate limiting no Connectivity Link?"

### 3. Validar Integração com MCP

Se o MCP Server do RHCL também estiver configurado, pergunte algo
que combine conhecimento BYOK + ação no cluster:

- "Crie um GatewayClass e um HTTPRoute para o serviço meu-app"

## Personalização

### Adicionar Seu Próprio Conteúdo

```bash
# Adicione arquivos .md
echo "# Minha Documentação Interna" > byok/content/minha-doc.md

# Reconstrua
make build
make push deploy
```

### Mudar Modelo de Embedding

```bash
make build EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Atualização Automática

Use **floating tags** (ex: `latest`) para que o OLS detecte
atualizações automaticamente:

```yaml
rag:
  - image: .../byok-rhcl:latest   # floating tag!
```

## Troubleshooting

### Erro: "rag field not recognized"

O campo `rag` é **Technology Preview**. Verifique:
- OpenShift Lightspeed 1.0+
- Indentação correta no OLSConfig
- O field está em `spec.ols.rag` (não `spec.llm.rag`)

### Erro: "ImagePullBackOff"

```bash
oc describe pod -n openshift-lightspeed -l app=lightspeed-app-server \
  | grep -A5 "Failed"

# Verificar se o registry está acessível
oc image info <pullspec>
```

### Erro: "vector_db_id not found"

O `indexID` no OLSConfig precisa corresponder ao `vector_db_id`
do metadata. Use `vector_db_index` (genérico) ou extraia do
`metadata.json` gerado:

```bash
cat byok/vector_db/output/metadata.json | jq .vector_db_id
```

## Referências

- [Red Hat Blog: Bring your own knowledge to OpenShift Lightspeed](https://www.redhat.com/en/blog/bring-your-own-knowledge-openshift-lightspeed)
- [Red Hat Docs: Configure OpenShift Lightspeed 1.0](https://docs.redhat.com/en/documentation/red_hat_openshift_lightspeed/1.0/html/configure/)
- [lightspeed-rag-content GitHub](https://github.com/openshift/lightspeed-rag-content)
- [Red Hat Connectivity Link Docs](https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/)
