# Makefile — BYOK (Bring Your Own Knowledge) para OpenShift Lightspeed
#
# Segue o fluxo oficial documentado pela Red Hat (OLS 1.0, Technology Preview):
# a imagem BYOK é gerada pela ferramenta lightspeed-rag-tool — NÃO há
# Containerfile próprio. A tool lê os markdowns, gera o vector database
# e produz um byok-image.tar pronto para carregar e publicar.
#
# Fluxo:
#   1. make build    Roda a lightspeed-rag-tool → output/byok-image.tar
#   2. make push     Carrega o tar, tagueia e envia para o registry
#   3. make deploy   Adiciona a imagem em spec.ols.rag do OLSConfig
#
# Pré-requisitos:
#   - Login no registry.redhat.io (para baixar a rag-tool)
#   - Login no registry destino (para o push)
#   - Conteúdo em content/ (somente arquivos .md)
#
# Funciona com podman OU docker — detecta automaticamente qual está ativo
# (sobrescreva com CONTAINER_TOOL=podman|docker).
#
# Docs: https://docs.redhat.com/en/documentation/red_hat_openshift_lightspeed/1.0/html-single/configure/index#providing-custom-knowledge-to-the-llm_ols-configuring-openshift-lightspeed

# ─── Configurações ──────────────────────────────────────────────────────────
IMAGE_NAME     ?= byok-rhcl
IMAGE_TAG      ?= latest
REGISTRY       ?= quay.io/<username>
CONTENT_DIR    ?= content
OUTPUT_DIR     ?= output
PLATFORM       ?= linux/amd64

RAG_TOOL_IMAGE ?= registry.redhat.io/openshift-lightspeed-tech-preview/lightspeed-rag-tool-rhel9:latest

# Mesmos parâmetros que a rag-tool usa internamente (Containerfile.output)
UBI_BASE_IMAGE  ?= registry.redhat.io/rhai/base-image-cpu-rhel9:3.3
VECTOR_DB_INDEX ?= vector_db_index
EMBED_MODEL     ?= sentence-transformers/all-mpnet-base-v2

# Nome fixo dos artefatos gerados pela rag-tool
TAR_FILE       := $(OUTPUT_DIR)/byok-image.tar
LOADED_IMAGE   := localhost/byok-image:latest
PULLSPEC       := $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

OC             := $(shell command -v oc 2>/dev/null || echo oc)

# Usa a primeira ferramenta com daemon/VM ATIVA (binário existir não basta)
CONTAINER_TOOL ?= $(shell if command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then echo podman; else echo docker; fi)

# Auth para o fluxo podman (montado dentro da rag-tool).
# No fluxo docker os pulls são feitos pelo docker do host (keychain nativo).
# Linux usa XDG_RUNTIME_DIR; macOS usa ~/.config
AUTH_JSON  ?= $(shell if [ -n "$$XDG_RUNTIME_DIR" ] && [ -f "$$XDG_RUNTIME_DIR/containers/auth.json" ]; then echo "$$XDG_RUNTIME_DIR/containers/auth.json"; else echo "$$HOME/.config/containers/auth.json"; fi)

# ─── Help ───────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo "BYOK — OpenShift Lightspeed (fluxo oficial lightspeed-rag-tool)"
	@echo ""
	@echo "Targets:"
	@echo "  build     Roda a rag-tool oficial e gera $(TAR_FILE)"
	@echo "  push      Carrega o tar, tagueia e envia para $(PULLSPEC)"
	@echo "  deploy    Configura spec.ols.rag no OLSConfig 'cluster'"
	@echo "  all       build + push"
	@echo "  clean     Remove $(OUTPUT_DIR)/"
	@echo ""
	@echo "Variáveis: REGISTRY=$(REGISTRY) IMAGE_NAME=$(IMAGE_NAME) IMAGE_TAG=$(IMAGE_TAG)"
	@echo "           CONTAINER_TOOL=$(CONTAINER_TOOL) PLATFORM=$(PLATFORM)"

# ─── Build ──────────────────────────────────────────────────────────────────
# podman: fluxo oficial da documentação — a rag-tool roda buildah interno e
#         produz output/byok-image.tar.
# docker: o buildah interno quebra (reexec sob emulação qemu no Mac ARM e
#         overlay-sobre-overlayfs). Replicamos o Containerfile.output da
#         própria tool em dois passos equivalentes: (1) docker run do
#         generate_embeddings_tool.py; (2) docker build só com COPY.
.PHONY: build
ifeq ($(CONTAINER_TOOL),docker)
build:
	@echo "=== Gerando imagem BYOK (docker, replicando o Containerfile.output da rag-tool) ==="
	rm -rf $(OUTPUT_DIR)/vector_db
	mkdir -p $(OUTPUT_DIR)/vector_db
	docker run $(shell [ -t 0 ] && echo -it) --rm --platform $(PLATFORM) \
		-v $(CURDIR)/$(CONTENT_DIR):/markdown \
		-v $(CURDIR)/$(OUTPUT_DIR)/vector_db:/workdir/vector_db \
		--entrypoint python3.12 $(RAG_TOOL_IMAGE) \
		generate_embeddings_tool.py -i /markdown -emd embeddings_model \
		-emn $(EMBED_MODEL) -o vector_db -id $(VECTOR_DB_INDEX)
	printf 'FROM %s\nCOPY vector_db /rag/vector_db\n' "$(UBI_BASE_IMAGE)" > $(OUTPUT_DIR)/Containerfile.byok
	docker build --platform $(PLATFORM) -f $(OUTPUT_DIR)/Containerfile.byok -t $(LOADED_IMAGE) $(OUTPUT_DIR)
	@echo "✓ Imagem gerada: $(LOADED_IMAGE)"
else
build:
	@echo "=== Gerando imagem BYOK via lightspeed-rag-tool (podman, fluxo oficial) ==="
	@if [ ! -f "$(AUTH_JSON)" ]; then \
		echo "ERRO: $(AUTH_JSON) não encontrado."; \
		echo "Faça login primeiro: $(CONTAINER_TOOL) login registry.redhat.io"; \
		exit 1; \
	fi
	mkdir -p $(OUTPUT_DIR)
	$(CONTAINER_TOOL) run $(shell [ -t 0 ] && echo -it) --rm --device /dev/fuse \
		-v $(AUTH_JSON):/run/user/0/containers/auth.json:Z \
		-v $(CURDIR)/$(CONTENT_DIR):/markdown:Z \
		-v $(CURDIR)/$(OUTPUT_DIR):/output:Z \
		$(RAG_TOOL_IMAGE)
	@test -f $(TAR_FILE) || { echo "ERRO: $(TAR_FILE) não foi gerado."; ls -la $(OUTPUT_DIR)/; exit 1; }
	$(CONTAINER_TOOL) load -i $(TAR_FILE)
	@echo "✓ Gerado: $(TAR_FILE) (carregado como $(LOADED_IMAGE))"
endif

# ─── Push (tag + push) ──────────────────────────────────────────────────────
.PHONY: push
push:
	@$(CONTAINER_TOOL) image inspect $(LOADED_IMAGE) >/dev/null 2>&1 \
		|| { echo "ERRO: $(LOADED_IMAGE) não existe. Rode 'make build' antes."; exit 1; }
	$(CONTAINER_TOOL) tag $(LOADED_IMAGE) $(PULLSPEC)
	$(CONTAINER_TOOL) push $(PULLSPEC)
	@echo "✓ Imagem publicada: $(PULLSPEC)"

# ─── Deploy (OLSConfig) ─────────────────────────────────────────────────────
.PHONY: deploy
deploy:
	@echo "=== Adicionando RAG BYOK ao OLSConfig ==="
	@$(OC) get olsconfig cluster >/dev/null || { echo "ERRO: OLSConfig 'cluster' não encontrado."; exit 1; }
	$(OC) patch olsconfig cluster --type merge -p \
		'{"spec":{"ols":{"rag":[{"image":"$(PULLSPEC)"}]}}}'
	@echo "✓ OLSConfig atualizado — o operator reinicia os pods do Lightspeed."

# ─── All ────────────────────────────────────────────────────────────────────
.PHONY: all
all: build push

# ─── Clean ──────────────────────────────────────────────────────────────────
.PHONY: clean
clean:
	rm -rf $(OUTPUT_DIR)/ .auth.json
	@echo "✓ $(OUTPUT_DIR)/ e .auth.json removidos"

# ─── Info ───────────────────────────────────────────────────────────────────
.PHONY: info
info:
	@echo "Tool:      $(CONTAINER_TOOL)"
	@echo "Platform:  $(PLATFORM)"
	@echo "Image:     $(PULLSPEC)"
	@echo "Rag tool:  $(RAG_TOOL_IMAGE)"
	@echo "Content:   $(CONTENT_DIR)/"
	@echo "Output:    $(OUTPUT_DIR)/"
	@echo "auth.json: $(AUTH_JSON)"
