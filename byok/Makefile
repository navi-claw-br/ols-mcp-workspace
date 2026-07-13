# Makefile — BYOK Image Builder para OpenShift Lightspeed
#
# Targets principais:
#   build              Constrói a imagem BYOK localmente
#   push               Envia a imagem para o registry
#   deploy             Atualiza o OLSConfig no cluster
#   all                build + push
#   tool-build         Usa o lightspeed-rag-tool oficial da Red Hat
#   clean              Remove artefatos locais
#
# Variáveis (sobrescreva via env ou make VAR=valor):
#
#   IMAGE_NAME         Nome da imagem (default: byok-rhcl)
#   IMAGE_TAG          Tag da imagem (default: latest)
#   REGISTRY           Registry destino (default: image-registry.openshift-image-registry.svc:5000)
#   REGISTRY_EXT       Registry externo acessível pelo cluster (default: usa o REGISTRY)
#   NAMESPACE          Namespace do OLS (default: openshift-lightspeed)
#   CONTENT_DIR        Diretório com documentos markdown (default: content)
#   OUTPUT_DIR         Diretório de saída do vector DB (default: ./vector_db/output)
#   EMBEDDING_MODEL    Modelo de embedding (default: sentence-transformers/all-mpnet-base-v2)
#

# ─── Configurações ──────────────────────────────────────────────────────────
IMAGE_NAME        ?= byok-rhcl
IMAGE_TAG         ?= latest
REGISTRY          ?= image-registry.openshift-image-registry.svc:5000
REGISTRY_EXT      ?= $(REGISTRY)
NAMESPACE         ?= openshift-lightspeed
CONTENT_DIR       ?= content
OUTPUT_DIR        ?= ./vector_db/output
EMBEDDING_MODEL   ?= sentence-transformers/all-mpnet-base-v2

OCTL             := $(shell command -v oc 2>/dev/null || echo "oc")
PODMAN           := $(shell command -v podman 2>/dev/null || echo "docker")

# ─── Help ───────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo "BYOK Image Builder — OpenShift Lightspeed"
	@echo ""
	@echo "Targets:"
	@echo "  build              Constrói a imagem BYOK (Containerfile)"
	@echo "  push               Push para o registry interno/externo"
	@echo "  deploy             Atualiza OLSConfig com a imagem BYOK"
	@echo "  all                build + push"
	@echo "  tool-build         Usa lightspeed-rag-tool oficial da Red Hat"
	@echo "  clean              Remove vetor_db/ local"
	@echo ""
	@echo "Variáveis:"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)  IMAGE_TAG=$(IMAGE_TAG)"
	@echo "  REGISTRY=$(REGISTRY)      NAMESPACE=$(NAMESPACE)"
	@echo ""

# ─── Build ──────────────────────────────────────────────────────────────────
.PHONY: build
build:
	@echo "=== Construindo imagem BYOK: $(IMAGE_NAME):$(IMAGE_TAG) ==="
	$(PODMAN) build \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		--build-arg EMBEDDING_MODEL=$(EMBEDDING_MODEL) \
		-f Containerfile .
	@echo ""
	@echo "✓ Imagem criada: $(IMAGE_NAME):$(IMAGE_TAG)"
	@echo "  Para ver: $(PODMAN) images $(IMAGE_NAME)"
	@echo ""
	@echo "Próximo passo: make push REGISTRY=<seu-registry>"

# ─── Push ───────────────────────────────────────────────────────────────────
.PHONY: push
push: PULLSPEC := $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
push:
	@echo "=== Pushendo para: $(PULLSPEC) ==="
	$(PODMAN) tag $(IMAGE_NAME):$(IMAGE_TAG) $(PULLSPEC)
	$(PODMAN) push $(PULLSPEC)
	@echo "✓ Imagem enviada: $(PULLSPEC)"

# ─── Push (registry externo) ────────────────────────────────────────────────
.PHONY: push-external
push-external: PULLSPEC := $(REGISTRY_EXT)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
push-external:
	@echo "=== Pushendo para registry externo: $(PULLSPEC) ==="
	$(PODMAN) tag $(IMAGE_NAME):$(IMAGE_TAG) $(PULLSPEC)
	$(PODMAN) push $(PULLSPEC)
	@echo "✓ Imagem enviada: $(PULLSPEC)"

# ─── Deploy (OLSConfig) ──────────────────────────────────────────────────
.PHONY: deploy
deploy: PULLSPEC := $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
deploy:
	@echo "=== Configurando OLSConfig com BYOK image ==="
	@if ! $(OCTL) get olsconfig cluster -n $(NAMESPACE) &>/dev/null; then \
		echo "ERRO: OLSConfig 'cluster' não encontrado. Crie-o primeiro."; \
		exit 1; \
	fi
	$(OCTL) patch olsconfig cluster -n $(NAMESPACE) --type merge -p \
		'{"spec":{"ols":{"rag":[{"image":"$(PULLSPEC)","indexID":"byok-rhcl","indexPath":"/rag/vector_db"}]}}}'
	@echo "✓ OLSConfig atualizado — pods do Lightspeed serão reiniciados."

# ─── All (build + push) ─────────────────────────────────────────────────────
.PHONY: all
all: build push
	@echo "✓ Build + push concluídos!"

# ─── Tool Build (via lightspeed-rag-tool oficial) ───────────────────────────
.PHONY: tool-build
tool-build: TAR_FILE := ./byok-image.tar
tool-build: LOADED_IMAGE := localhost/byok-image:latest
tool-build:
	@echo "=== Usando lightspeed-rag-tool oficial da Red Hat ==="
	@echo ""
	@echo "Requer:"
	@echo "  - Acesso ao registry.redhat.io (oc registry login)"
	@echo "  - Podman instalado"
	@echo ""
	@echo "Step 1: Executando a tool..."
	mkdir -p $(OUTPUT_DIR)
	$(PODMAN) run -it --rm --device=/dev/fuse \
		-v $$XDG_RUNTIME_DIR/containers/auth.json:/run/user/0/containers/auth.json:Z \
		-v $(PWD)/$(CONTENT_DIR):/markdown:Z \
		-v $(PWD)/$(OUTPUT_DIR):/output:Z \
		registry.redhat.io/openshift-lightspeed-tech-preview/lightspeed-rag-tool-rhel9:latest
	@echo ""
	@echo "Step 2: Carregando a imagem gerada..."
	$(PODMAN) load -i $(OUTPUT_DIR)/byok-image.tar
	@echo ""
	@echo "Step 3: Tagueando e pushendo..."
	$(PODMAN) tag $(LOADED_IMAGE) $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
	$(PODMAN) push $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo ""
	@echo "✓ Imagem BYOK criada via tool oficial!"
	@echo "  $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)"
	@echo ""
	@echo "Configure no OLSConfig:"
	@echo '  spec.ols.rag:'
	@echo '    - image: $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)'
	@echo '      indexID: vector_db_index'
	@echo '      indexPath: /rag/vector_db'

# ─── Clean ──────────────────────────────────────────────────────────────────
.PHONY: clean
clean:
	rm -rf ./vector_db/
	@echo "✓ Artefatos removidos (vector_db/)"

# ─── Info ───────────────────────────────────────────────────────────────────
.PHONY: info
info:
	@echo "Configuração atual:"
	@echo "  Image:    $(IMAGE_NAME):$(IMAGE_TAG)"
	@echo "  Registry: $(REGISTRY)"
	@echo "  Ns:       $(NAMESPACE)"
	@echo "  Content:  $(CONTENT_DIR)/"
	@echo "  Model:    $(EMBEDDING_MODEL)"
	@echo "  Container:$(PODMAN)"
	@echo "  OLS CLI:  $(OCTL)"
