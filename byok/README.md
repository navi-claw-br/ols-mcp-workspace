# BYOK — Bring Your Own Knowledge para OpenShift Lightspeed

Este diretório contém o conteúdo e a automação para criar uma **imagem BYOK**
com documentação do **Red Hat Connectivity Link** e disponibilizá-la como
conhecimento customizado no OpenShift Lightspeed (OLS 1.0, Technology Preview).

O fluxo segue a [documentação oficial da Red Hat][docs-byok]: a imagem é
gerada pela ferramenta **`lightspeed-rag-tool`** — não há Containerfile
próprio nem indexação manual. A tool lê os markdowns, constrói o vector
database no formato que o OLS espera e empacota tudo num `byok-image.tar`.

## Pré-requisitos

- Acesso ao console do OpenShift com permissão de `cluster-admin` (ou
  permissão para editar CRs cluster-scoped)
- OpenShift Lightspeed Operator instalado e um provedor LLM configurado
- Documentos em **Markdown** (somente extensão `.md`) — já estão em `content/`
- `podman` com login no `registry.redhat.io` (para baixar a rag-tool)
- Conta em um registry de container acessível pelo cluster (ex.: `quay.io`)

```bash
podman login registry.redhat.io
podman login quay.io
```

## Quick Start

```bash
# 1. Gera a imagem BYOK (produz output/byok-image.tar)
make build

# 2. Carrega o tar, tagueia e envia para o registry
make push REGISTRY=quay.io/<username>

# 3. Configura o OLSConfig do cluster
make deploy REGISTRY=quay.io/<username>
```

## O que cada passo faz

### 1. `make build` — gera a imagem via rag-tool oficial

Equivalente ao comando da documentação:

```bash
podman run -it --rm --device=/dev/fuse \
  -v $XDG_RUNTIME_DIR/containers/auth.json:/run/user/0/containers/auth.json:Z \
  -v ./content:/markdown:Z \
  -v ./output:/output:Z \
  registry.redhat.io/openshift-lightspeed-tech-preview/lightspeed-rag-tool-rhel9:latest
```

O resultado é `output/byok-image.tar`.

> **podman ou docker:** o Makefile detecta automaticamente qual ferramenta
> está com o daemon/VM ativo (sobrescreva com `CONTAINER_TOOL=podman|docker`)
> e roda a tool com `--platform linux/amd64` (ajuste via `PLATFORM=`).
>
> **docker no macOS:** o Docker Desktop guarda credenciais no keychain, não
> no `config.json`. O target `gen-auth` (chamado automaticamente pelo build)
> extrai a credencial do `registry.redhat.io` para um `.auth.json` plano
> (gitignored) que é montado na tool. Requer `docker login registry.redhat.io`
> feito previamente.

### 2. `make push` — carrega e publica

Equivalente a:

```bash
podman load -i output/byok-image.tar          # carrega como localhost/byok-image:latest
podman tag localhost/byok-image:latest quay.io/<username>/byok-rhcl:latest
podman push quay.io/<username>/byok-rhcl:latest
```

### 3. `make deploy` — configura o OLSConfig

Adiciona a imagem em `spec.ols.rag` (pode-se listar várias imagens BYOK):

```yaml
apiVersion: ols.openshift.io/v1alpha1
kind: OLSConfig
metadata:
  name: cluster
spec:
  ols:
    rag:
      - image: quay.io/<username>/byok-rhcl:latest
```

Alternativamente, aplique o patch manualmente:

```bash
oc patch olsconfig cluster --type merge --patch-file olsconfig-patch.yaml
```

O Lightspeed Operator reinicia os pods do `lightspeed-app-server`
automaticamente.

## Opções adicionais

### Usar somente o conhecimento BYOK

Para o serviço responder **apenas** com base nas suas imagens BYOK, sem a
base padrão de documentação do OpenShift:

```yaml
spec:
  ols:
    byokRAGOnly: true
```

### Registry privado

```yaml
spec:
  ols:
    imagePullSecrets:
      - name: <my_pull_secret>
```

## Verificação

```bash
# Pods devem reiniciar após o deploy
oc get pods -n openshift-lightspeed -w

# No console do OpenShift, pergunte algo que use o conhecimento do RHCL:
# "Como configurar uma TLSPolicy no Red Hat Connectivity Link?"
```

## Atualizar o conteúdo

```bash
# 1. Edite/adicione arquivos .md em content/
# 2. Regenere e republique:
make clean build push deploy REGISTRY=quay.io/<username>
```

## Estrutura

```
byok/
├── README.md              ← Você está aqui
├── Makefile               ← build / push / deploy (fluxo oficial)
├── olsconfig-patch.yaml   ← Patch de exemplo para o OLSConfig
├── content/               ← Documentos markdown do RHCL (input da rag-tool)
└── output/                ← byok-image.tar gerado (gitignored)
```

## Referências

- [Providing custom knowledge to the LLM — OLS 1.0 Configure][docs-byok]
- [Blog: Bring your own knowledge to OpenShift Lightspeed](https://www.redhat.com/en/blog/bring-your-own-knowledge-openshift-lightspeed)
- [Red Hat Connectivity Link Documentation](https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/)

[docs-byok]: https://docs.redhat.com/en/documentation/red_hat_openshift_lightspeed/1.0/html-single/configure/index#providing-custom-knowledge-to-the-llm_ols-configuring-openshift-lightspeed
