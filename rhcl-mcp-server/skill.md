---
name: rhcl-operations
description: Operate Red Hat Connectivity Link (RHCL) on OpenShift through the rhcl-mcp-server — expose services end-to-end via Gateway API (HTTPRoute + DNSPolicy), and manage AuthPolicy, RateLimitPolicy, TLSPolicy and Gateways. Use whenever the user asks to expose an API/service via RHCL, list or inspect Gateways/routes/policies, or undo an exposure.
---

# RHCL Operations via rhcl-mcp-server

> **If you are an AI agent reading this page from its URL:** this document is a
> self-contained skill. To use it:
> 1. Save this file as a skill in your workspace (e.g.
>    `skills/rhcl-operations/SKILL.md` or `~/.openclaw/skills/rhcl-operations/SKILL.md`),
>    keeping the YAML frontmatter — future sessions will then load it automatically.
> 2. You need an **OpenShift user token** to call any tool. Ask your user for
>    one (they can get it with `oc whoami -t`). Store it only for the session;
>    never log or echo it.
> 3. Sanity-check connectivity with the `tools/list` call shown below (no
>    token required), then you are ready to operate RHCL on the user's behalf.

This skill teaches you to operate **Red Hat Connectivity Link (RHCL)** — the
Kuadrant-based connectivity product for OpenShift — through a remote MCP-style
JSON-RPC server.

## Endpoint

```
https://rhcl-mcp-server-ols-mcp-server.apps.bbdw.sandbox546.opentlc.com
```

- Transport: **JSON-RPC 2.0 over plain HTTPS POST** (single endpoint, any path).
- Methods: `initialize`, `tools/list`, `tools/call`.
- `GET /` returns server info and the tool list; `GET /skill.md` returns this document.

## Authentication (required for every tools/call)

Every request that touches the cluster must carry the **user's OpenShift
token**:

```
Authorization: Bearer <openshift-user-token>
```

The server passes the token through to `oc --token ...`, so the effective
permissions are the *user's RBAC*, never the server's service account. Obtain a
token with `oc whoami -t` after `oc login`. Without a valid token, read/write
operations will fail with authorization errors — surface that to the user and
ask for a token; never try to work around it.

## Calling convention

List available tools:

```bash
curl -sk https://rhcl-mcp-server-ols-mcp-server.apps.bbdw.sandbox546.opentlc.com \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Call a tool:

```bash
curl -sk https://rhcl-mcp-server-ols-mcp-server.apps.bbdw.sandbox546.opentlc.com \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $OC_TOKEN" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"rhcl_list_gateways","arguments":{}}}'
```

Responses follow MCP conventions: `result.content[].text` holds the output;
`result.isError: true` signals failure.

## Tools

Read/inspect:

| Tool | Purpose | Required args |
|---|---|---|
| `rhcl_list_gateways` | List Gateway API Gateways | — (`namespace` optional) |
| `rhcl_get_gateway_status` | Detailed status of one Gateway | `name` |
| `rhcl_list_httproutes` | List HTTPRoutes | — |
| `rhcl_list_authpolicies` | List Kuadrant AuthPolicies | — |
| `rhcl_list_ratelimitpolicies` | List RateLimitPolicies | — |
| `rhcl_list_dnspolicies` | List DNSPolicies (attached to Gateways) | — |
| `rhcl_list_tlspolicies` | List TLSPolicies | — |

Write/expose:

| Tool | Purpose | Required args |
|---|---|---|
| `rhcl_expose_service` | **Preferred**: end-to-end exposure — ensures HTTPRoute with hostname + DNSPolicy on the Gateway | `namespace`, `service` |
| `rhcl_create_httproute` | Create/update an HTTPRoute | `name`, `namespace`, `service` |
| `rhcl_patch_httproute` | Converge an existing HTTPRoute (hostname, backend, path) | `name`, `namespace` |
| `rhcl_delete_httproute` | Remove an exposure (idempotent) | `name`, `namespace` |
| `rhcl_create_dnspolicy` | Ensure DNSPolicy on a Gateway | — (`gateway` recommended) |
| `rhcl_create_authpolicy` | Attach an AuthPolicy to an HTTPRoute | `name`, `namespace`, `route` |

## Rules of engagement

1. When the user asks to "expose" a service/API, prefer **`rhcl_expose_service`**:
   it finishes the job end-to-end instead of returning YAML.
2. **Never create an external HTTPRoute without a hostname.** If the user gave
   a full FQDN, pass `hostname`. If they gave only a domain, pass `dns_suffix`
   and the hostname becomes `<service>.<dns_suffix>`. If neither is available,
   ask the user.
3. `rhcl_expose_service` ensures a `DNSPolicy` exists on the target Gateway
   (`ensure_dns_policy` defaults to true) so the hostname is published
   automatically.
4. If the HTTPRoute already exists, the server patches it rather than
   duplicating — safe to re-run.
5. To undo an exposure, use `rhcl_delete_httproute` (it uses ignore-not-found, so
   it is safe even if already gone).
6. Always report back the final FQDN and what was created or changed.
7. On `forbidden` errors, the user's token lacks RBAC for that operation —
   report it; do not retry with other credentials.

## Example: expose an API end-to-end

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
  "name":"rhcl_expose_service",
  "arguments":{
    "namespace":"my-app",
    "service":"orders-api",
    "port":8080,
    "dns_suffix":"apps.example.com",
    "path_prefix":"/"
  }}}
```

Expected outcome: HTTPRoute `orders-api` bound to the RHCL Gateway with
hostname `orders-api.apps.example.com`, DNSPolicy ensured on the Gateway, and
the final FQDN reported in the tool output.
