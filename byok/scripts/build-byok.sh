#!/usr/bin/env bash
# build-byok.sh — Build da imagem BYOK para OpenShift Lightspeed
#
# Duas estratégias:
#   1. OFICIAL (tool): usa lightspeed-rag-tool da Red Hat (registry.redhat.io)
#   2. DIRETA (Containerfile): build local sem dependência externa (padrão)
#
# Uso:
#   ./scripts/build-byok.sh                      # Build direto (Containerfile)
#   ./scripts/build-byok.sh --tool               # Build via tool oficial
#   ./scripts/build-byok.sh --tool --push        # Build + push
#   ./scripts/build-byok.sh --push               # Build direto + push
#
# Variáveis de ambiente:
#   BYOK_IMAGE       Nome da imagem (default: byok-rhcl)
#   BYOK_TAG         Tag (default: latest)
#   BYOK_REGISTRY    Registry destino
#   BYOK_NAMESPACE   Namespace OLS (default: openshift-lightspeed)
#   CONTENT_DIR      Diretório dos markdowns (default: content)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ─── Config ────────────────────────────────────────────────────────────────
BYOK_IMAGE="${BYOK_IMAGE:-byok-rhcl}"
BYOK_TAG="${BYOK_TAG:-latest}"
BYOK_REGISTRY="${BYOK_REGISTRY:-}"
BYOK_NAMESPACE="${BYOK_NAMESPACE:-openshift-lightspeed}"
CONTENT_DIR="${CONTENT_DIR:-content}"
BYOK_CONTAINER_TOOL="${BYOK_CONTAINER_TOOL:-$(command -v podman || command -v docker || echo "podman")}"

USE_TOOL=false
DO_PUSH=false

# ─── Help ──────────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
build-byok.sh — Build da imagem BYOK para OpenShift Lightspeed

Uso:
  $(basename "$0") [opções]

Opções:
  --tool         Usa lightspeed-rag-tool oficial da Red Hat
  --push         Push para o registry após build
  --registry R   Registry destino (ex: quay.io/meuuser)
  --tag T        Tag da imagem (default: latest)
  --help         Esta ajuda

Exemplos:
  # Build direto (Containerfile)
  ./scripts/build-byok.sh

  # Build + push para registry externo
  ./scripts/build-byok.sh --push --registry quay.io/meuuser

  # Build via tool oficial da Red Hat
  ./scripts/build-byok.sh --tool

  # Build tool + push para registry do cluster
  ./scripts/build-byok.sh --tool --push

Variáveis de ambiente:
  BYOK_IMAGE, BYOK_TAG, BYOK_REGISTRY, BYOK_NAMESPACE, CONTENT_DIR
EOF
    exit 0
}

# ─── Parse args ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool)     USE_TOOL=true; shift ;;
        --push)     DO_PUSH=true; shift ;;
        --registry) BYOK_REGISTRY="$2"; shift 2 ;;
        --tag)      BYOK_TAG="$2"; shift 2 ;;
        --help|-h)  usage ;;
        *) echo "Opção desconhecida: $1"; usage ;;
    esac
done

# ─── 1. Build direto (Containerfile) ──────────────────────────────────────
build_direct() {
    echo "=== Build DIRETO via Containerfile ==="
    echo "  Imagem: ${BYOK_IMAGE}:${BYOK_TAG}"
    echo "  Content: ${CONTENT_DIR}/"
    echo ""

    cd "${REPO_DIR}"

    if [ ! -f Containerfile ]; then
        echo "ERRO: Containerfile não encontrado em ${REPO_DIR}"
        exit 1
    fi

    ${BYOK_CONTAINER_TOOL} build \
        -t "${BYOK_IMAGE}:${BYOK_TAG}" \
        -f Containerfile \
        .

    echo ""
    echo "✓ Imagem criada: ${BYOK_IMAGE}:${BYOK_TAG}"
    ${BYOK_CONTAINER_TOOL} images "${BYOK_IMAGE}:${BYOK_TAG}"
}

# ─── 2. Build via tool oficial da Red Hat ─────────────────────────────────
build_tool() {
    echo "=== Build via lightspeed-rag-tool oficial (Red Hat) ==="
    echo ""
    echo "Pré-requisitos:"
    echo "  - Login no registry.redhat.io"
    echo "  - Podman instalado"
    echo ""

    cd "${REPO_DIR}"

    # Verifica se está logado no registry.redhat.io
    if ! ${BYOK_CONTAINER_TOOL} login --get-login registry.redhat.io &>/dev/null; then
        echo "⚠  Você precisa fazer login no registry.redhat.io primeiro:"
        echo "   ${BYOK_CONTAINER_TOOL} login registry.redhat.io"
        echo ""
        echo "   Para obter credenciais: https://access.redhat.com/RegistryAuthentication"
        echo ""
        read -rp "Deseja continuar mesmo assim? (s/N): " resp
        if [[ ! "$resp" =~ ^[sSyY] ]]; then
            echo "Abortando."
            exit 1
        fi
    fi

    OUTPUT_DIR="${REPO_DIR}/vector_db/output"
    mkdir -p "${OUTPUT_DIR}"

    echo "Step 1/3: Executando lightspeed-rag-tool..."
    echo "  Content: ${CONTENT_DIR}/"
    echo "  Output:  ${OUTPUT_DIR}/"
    echo ""

    ${BYOK_CONTAINER_TOOL} run -it --rm --device=/dev/fuse \
        -v "${XDG_RUNTIME_DIR}/containers/auth.json:/run/user/0/containers/auth.json:Z" \
        -v "${REPO_DIR}/${CONTENT_DIR}:/markdown:Z" \
        -v "${OUTPUT_DIR}:/output:Z" \
        registry.redhat.io/openshift-lightspeed-tech-preview/lightspeed-rag-tool-rhel9:latest

    echo ""
    echo "Step 2/3: Carregando imagem gerada..."
    TAR_FILE="${OUTPUT_DIR}/byok-image.tar"
    if [ ! -f "${TAR_FILE}" ]; then
        echo "ERRO: ${TAR_FILE} não encontrado!"
        echo "  A tool pode ter gerado em outro caminho. Verifique ${OUTPUT_DIR}/"
        ls -la "${OUTPUT_DIR}/"
        exit 1
    fi

    ${BYOK_CONTAINER_TOOL} load -i "${TAR_FILE}"

    echo ""
    echo "✓ Tool concluída! Imagem carregada como localhost/byok-image:latest"
    echo ""
}

# ─── Push ────────────────────────────────────────────────────────────────────
do_push() {
    if [ -z "${BYOK_REGISTRY}" ]; then
        echo ""
        echo "⚠  BYOK_REGISTRY não definido. Informe o registry:"
        echo "   Ex: quay.io/meuuser, image-registry.openshift-image-registry.svc:5000"
        echo ""
        echo "   Para pular o push:"
        echo "     make push REGISTRY=<registry>"
        echo "     ou export BYOK_REGISTRY=<registry> && ./scripts/build-byok.sh --push"
        echo ""
        return
    fi

    PULLSPEC="${BYOK_REGISTRY}/${BYOK_NAMESPACE}/${BYOK_IMAGE}:${BYOK_TAG}"

    if ${USE_TOOL}; then
        SOURCE_IMAGE="localhost/byok-image:latest"
    else
        SOURCE_IMAGE="${BYOK_IMAGE}:${BYOK_TAG}"
    fi

    echo ""
    echo "=== Pushendo imagem ==="
    echo "  Source: ${SOURCE_IMAGE}"
    echo "  Dest:   ${PULLSPEC}"
    echo ""

    ${BYOK_CONTAINER_TOOL} tag "${SOURCE_IMAGE}" "${PULLSPEC}"
    ${BYOK_CONTAINER_TOOL} push "${PULLSPEC}"

    echo ""
    echo "✓ Imagem publicada: ${PULLSPEC}"
    echo ""
    echo "Configure no OLSConfig:"
    echo ""
    echo "spec:"
    echo "  ols:"
    echo "    rag:"
    echo "      - image: ${PULLSPEC}"
    echo "        indexID: vector_db_index"
    echo "        indexPath: /rag/vector_db"
}

# ─── Main ──────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   BYOK Image Builder — OpenShift Lightspeed         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

if ${USE_TOOL}; then
    build_tool
else
    build_direct
fi

if ${DO_PUSH}; then
    do_push
fi

echo ""
echo "✓ Concluído!"
echo ""
