#!/usr/bin/env bash
# index-content.sh - Indexa o conteudo BYOK para o Lightspeed Core
#
# Requer:
#   - Python 3.12+
#   - rag-content tool (https://github.com/lightspeed-core/rag-content)
#   - modelo de embedding (default: sentence-transformers/all-mpnet-base-v2)
#
# Uso:
#   ./index-content.sh [diretorio-docs] [output-dir]
set -euo pipefail

CONTENT_DIR="${1:-content}"
OUTPUT_DIR="${2:-./vector_db}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-sentence-transformers/all-mpnet-base-v2}"

echo "=== Indexacao BYOK - Red Hat Connectivity Link ==="

# Verificar dependencias
if ! command -v uv &> /dev/null; then
    echo "Erro: uv nao encontrado. Instale com: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if [ ! -d "../rag-content" ]; then
    echo "Clonando rag-content..."
    git clone https://github.com/lightspeed-core/rag-content.git ../rag-content
fi

echo ""
echo "[1/4] Preparando documentos markdown..."
DOCS_DIR="${OUTPUT_DIR}/docs"
mkdir -p "${DOCS_DIR}"
cp "${CONTENT_DIR}"/*.md "${DOCS_DIR}/"

echo "[2/4] Download do modelo de embedding..."
mkdir -p "${OUTPUT_DIR}/embeddings_model"
uv run python ../rag-content/scripts/download_embeddings_model.py \
    -l "${OUTPUT_DIR}/embeddings_model/" \
    -r "${EMBEDDING_MODEL}"

echo "[3/4] Indexando documentos com rag-content..."
uv run python ../rag-content/rag_content/main.py \
    -i "${DOCS_DIR}" \
    -o "${OUTPUT_DIR}" \
    -t md \
    -e "${OUTPUT_DIR}/embeddings_model/" \
    --embedding-model "${EMBEDDING_MODEL}" \
    --custom-processor scripts/custom_processor.py \
    --chunk-size 1000 \
    --chunk-overlap 200

echo "[4/4] Verificando resultado..."
if [ -f "${OUTPUT_DIR}/faiss_store.db" ]; then
    VECTOR_DB_ID=$(sqlite3 "${OUTPUT_DIR}/faiss_store.db" \
        "SELECT value FROM metadata WHERE key='vector_db_id'" 2>/dev/null || echo "unknown")
    echo ""
    echo "=== Indexacao concluida! ==="
    echo "Vector DB: ${OUTPUT_DIR}/faiss_store.db"
    echo "Vector DB ID: ${VECTOR_DB_ID}"
    echo ""
    echo "Configure o lightspeed-stack.yaml com:"
    echo "  rag_id: rh-connectivity-link"
    echo "  vector_db_id: ${VECTOR_DB_ID}"
    echo "  db_path: ${OUTPUT_DIR}/faiss_store.db"
else
    echo "ERRO: Arquivo faiss_store.db nao encontrado!"
    exit 1
fi
