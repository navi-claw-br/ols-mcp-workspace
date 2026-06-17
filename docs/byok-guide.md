# Guia BYOK - Red Hat Connectivity Link

## Visão Geral

BYOK (Bring Your Own Knowledge) permite adicionar conhecimento customizado ao Lightspeed Core Service usando RAG (Retrieval-Augmented Generation). Este guia cobre a criação de uma base de conhecimento sobre **Red Hat Connectivity Link**.

## Arquitetura BYOK

O Lightspeed Core Service suporta dois modos de BYOK:

1. **Inline RAG**: Contexto é buscado automaticamente do vector store e injetado antes de cada query LLM
2. **Tool RAG**: LLM pode chamar a tool `file_search` para buscar contexto sob demanda

Ambos os modos usam:
- **Vector Database**: FAISS (local) ou pgvector (PostgreSQL)
- **Embedding Model**: Converte consultas e documentos em vetores para busca por similaridade

## Pré-requisitos BYOK

- Lightspeed Core Service instalado
- Python 3.12+ com `uv`
- [rag-content tool](https://github.com/lightspeed-core/rag-content)
- Modelo de embedding (default: `sentence-transformers/all-mpnet-base-v2`)

## Conteúdo Preparado

O diretório `byok/content/` contém documentação markdown do Red Hat Connectivity Link:

| Arquivo | Conteúdo |
|---------|----------|
| 01-overview.md | Visão geral e conceitos |
| 02-architecture.md | Arquitetura e componentes |
| 03-installation.md | Instalação via OperatorHub |
| 04-gateway-api.md | Gateway API (GatewayClass, Gateway, HTTPRoute) |
| 05-tls-policies.md | Políticas TLS (TLSPolicy, cert-manager) |
| 06-auth-policies.md | Autenticação e Autorização (AuthPolicy) |
| 07-rate-limiting.md | Rate Limiting (RateLimitPolicy) |
| 08-dns-multicluster.md | DNS Multicluster (DNSPolicy) |
| 09-observability.md | Observabilidade (métricas, dashboards, alertas) |

## Passo a Passo

### 1. Indexar o Conteúdo

```bash
cd byok/scripts
./index-content.sh ../content ./output
```

Isso vai:
1. Copiar os documentos markdown
2. Baixar o modelo de embedding
3. Indexar os documentos com `rag-content`
4. Gerar o vector database FAISS

### 2. Atualizar a Configuração

Após a indexação, atualize o `lightspeed-stack.yaml`:

```bash
# O script mostra o vector_db_id gerado
# Edite byok/lightspeed-stack.yaml e atualize:
#   vector_db_id: <id-gerado>
#   db_path: /path/to/output/faiss_store.db
```

### 3. Iniciar o Lightspeed Core Service

```bash
# Com docker-compose
docker-compose -f lightspeed-stack.yaml up -d

# Ou com make
make run
```

### 4. Verificar

```bash
# Testar a query
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "O que e o Red Hat Connectivity Link?"}'
```

## Personalização

### Adicionar Mais Documentos

Adicione arquivos `.md` em `byok/content/` e reindexe:

```bash
cp novo-documento.md byok/content/
./index-content.sh byok/content ./output
```

### Custom Processor

O arquivo `scripts/custom_processor.py` define metadados como URLs de referência. Edite conforme necessário para adicionar mais mapeamentos.

## Integração com OpenShift Lightspeed

O BYOK do Lightspeed Core é independente do OpenShift Lightspeed Operator. Para usar o conhecimento do Connectivity Link no OpenShift Lightspeed:

### Opção 1: Lightspeed Core + OpenShift Lightspeed

Configure o Lightspeed Core como LLM provider do OpenShift Lightspeed:

```yaml
# OLSConfig
spec:
  llm:
    providers:
      - name: lightspeed-core
        type: openai  # Lightspeed Core expoe API compatível com OpenAI
        url: http://lightspeed-core-service:8080/v1
        credentialsSecretRef:
          name: lightspeed-core-credentials
        models:
          - name: default
```

### Opção 2: Referência Manual

Adicione o conteúdo como attachment nas queries do OpenShift Lightspeed:

```bash
curl -X POST https://${OLS_HOST}/v1/query \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Como configurar TLS no Connectivity Link?",
    "attachments": [
      {
        "type": "text/markdown",
        "content": "... conteudo do byok/content/ ..."
      }
    ]
  }'
```

## Fontes de Dados

O conhecimento foi compilado das seguintes fontes oficiais:
- https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/
- https://kuadrant.io/
- https://gateway-api.sigs.k8s.io/
