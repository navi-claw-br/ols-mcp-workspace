# Autenticação MCP - Como o Token do Usuário é Usado

## Visão Geral

O MCP server recebe o token do usuário que está logado no OpenShift Console e o utiliza para autenticar todas as operações na API do OpenShift. Isso significa que **as permissões do RBAC do usuário são respeitadas** — o MCP server nunca opera com privilégios maiores que o usuário logado.

## Fluxo de Autenticação Detalhado

```
1. Usuario logado no OpenShift Console (token OAuth valido)
           |
2. Usuario faz pergunta no Lightspeed
           |
3. Lightspeed valida o token:
   - TokenReview: verifica se o token é valido
   - SubjectAccessReview: verifica se o usuario tem acesso a /ols-access
           |
4. Lightspeed identifica que precisa de uma tool MCP
           |
5. Lightspeed chama o endpoint do MCP server:
   POST /mcp
   Headers:
     Authorization: Bearer <token-do-usuario>
           |
6. MCP server recebe o token
           |
7. MCP server usa o token para autenticar na API do OpenShift:
   - Cria um client kubernetes com o token Bearer
   - Faz a operacao solicitada (list pods, get deployment, etc.)
           |
8. OpenShift API Server valida o token e as permissoes RBAC
   - Se o usuario tem permissao → operacao executada
   - Se nao tem permissao → erro 403 retornado
           |
9. MCP server retorna resultado para o Lightspeed
           |
10. Lightspeed usa o resultado na resposta para o usuario
```

## Configuração no OLSConfig

O segredo está na configuração do header no OLSConfig:

```yaml
mcpServers:
  - name: openshift-mcp-server
    url: http://kubernetes-mcp-server.kubernetes-mcp-server.svc.cluster.local:8080/mcp
    timeout: 120
    headers:
      - name: Authorization
        valueFrom:
          type: kubernetes    # <-- Isso faz o Lightspeed enviar o token do usuario
```

Quando `valueFrom.type: kubernetes` é configurado, o Lightspeed automaticamente:
1. Pega o token Bearer da requisição original do usuário
2. Adiciona no header `Authorization` da chamada ao MCP server
3. O MCP server recebe o token e o utiliza para autenticar na API

## Modo Passthrough no MCP Server

O openshift-mcp-server suporta o modo `cluster_auth_mode = "passthrough"` no config.toml:

```toml
cluster_auth_mode = "passthrough"
```

Neste modo, o MCP server:
1. Extrai o token Bearer do header `Authorization` recebido
2. Cria um client Kubernetes configurado com esse token
3. Todas as operações são executadas com as permissões do token
4. **Não usa** o ServiceAccount do pod — use o token do usuário

## Segurança

### O que o MCP server NÃO pode fazer

O MCP server não consegue operar além das permissões do usuário:
- Se o usuário é apenas `view`, só pode ler recursos
- Se o usuário tem permissões de admin, pode criar/deletar recursos
- **Nunca**: ler Secrets (bloqueado no `denied_resources` do config.toml)
- **Nunca**: modificar RBAC (bloqueado no `denied_resources`)

### Proteções Adicionais

1. **Read-only mode**: Configure `read_only = true` no config.toml para ambientes produtivos
2. **Denied Resources**: Bloqueie recursos sensíveis (Secrets, RBAC)
3. **Tool filtering**: O Lightspeed pode filtrar quais tools ficam disponíveis
4. **Approval**: Configure `approvalType: tool_annotations` no OLSConfig para exigir aprovação humana

### Exemplo de Configuração Segura para Produção

```toml
# config.toml - Configuracao de producao
log_level = 2
read_only = true                     # Apenas leitura
disable_destructive = true           # Sem operacoes destrutivas
cluster_auth_mode = "passthrough"    # Usa token do usuario
disable_multi_cluster = true         # Apenas cluster atual

# Bloquear recursos sensiveis
[[denied_resources]]
group = ""
version = "v1"
kind = "Secret"

[[denied_resources]]
group = "rbac.authorization.k8s.io"
version = "v1"
kind = "ClusterRole"
```

## Monitoramento

Para auditar as operações do MCP server:

```bash
# Logs do MCP server
oc logs -n kubernetes-mcp-server deployment/kubernetes-mcp-server

# Métricas do MCP server
oc port-forward -n kubernetes-mcp-server deployment/kubernetes-mcp-server 8080:8080
curl http://localhost:8080/stats

# Auditoria no OpenShift
oc get events --all-namespaces --field-selector involvedObject.kind=Pod
```

## Falha comum em MCP customizado

Se um MCP customizado mistura operacoes de leitura e escrita, nao basta
propagar o token apenas no caminho de `get/list`. Operacoes como
`create/apply/patch` tambem precisam usar explicitamente o token recebido
no header `Authorization`.

Sintoma tipico:

```text
system:serviceaccount:ols-mcp-server:ols-mcp-server cannot create httproutes
```

Interpretacao:

- se o erro cita a service account do pod, o passthrough falhou
- se o erro cita o usuario real, o passthrough funcionou e o problema e RBAC

Para o runbook completo de validacao do servidor RHCL, veja:

- `docs/rhcl-mcp-server-runbook.md`
