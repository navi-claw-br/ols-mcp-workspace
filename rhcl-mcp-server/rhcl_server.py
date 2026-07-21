#!/usr/bin/env python3
"""RHCL MCP Server - Tools especializados para Red Hat Connectivity Link.

Este servidor MCP fornece tools especificas para operar o RHCL:
- Listar Gateways, HTTPRoutes e policies do Kuadrant
- Expor servicos com HTTPRoute + hostname
- Garantir DNSPolicy no Gateway quando necessario
- Diagnosticar Gateways
"""

import json
import os
import subprocess
import sys
from typing import Any

# Token do usuario, enviado via Authorization header OLSConfig
# Extraido a cada request e usado no comando oc
_user_token = ""


def set_user_token(token: str):
    """Define o token do usuario para usar nos comandos oc."""
    global _user_token
    _user_token = token or ""


def get_oc_args(extra_args: list[str]) -> list[str]:
    """Retorna a lista de args para oc, com token se disponivel."""
    cmd = ["oc"]
    if _user_token:
        cmd += ["--token", _user_token]
    return cmd + extra_args


def run_oc(args: list[str]) -> tuple[int, str]:
    """Executa um comando oc com o token do usuario e retorna (returncode, output)."""
    cmd = get_oc_args(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Timeout executing oc command"
    except FileNotFoundError:
        return 1, "oc binary not found"
    except Exception as e:
        return 1, str(e)


def oc_get_resource(group: str, version: str, kind: str, namespace: str = "",
                    name: str = "", output: str = "yaml") -> dict[str, Any]:
    """Lista ou obtem um recurso Kubernetes."""
    args = ["get"]
    if namespace and namespace != "ALL":
        args += ["-n", namespace]
    elif namespace == "ALL":
        args += ["-A"]

    resource = kind.lower()
    if group:
        resource = f"{resource}.{group}"
    args.append(resource)

    if name:
        args.append(name)
    args += ["-o", output]

    rc, out = run_oc(args)
    return {"success": rc == 0, "output": out, "error": None if rc == 0 else out}


def oc_create_resource(yaml_content: str, namespace: str = "") -> dict[str, Any]:
    """Cria um recurso Kubernetes a partir de YAML."""
    args = ["create", "-f", "-"]
    if namespace:
        args += ["-n", namespace]

    try:
        result = subprocess.run(
            get_oc_args(args),
            input=yaml_content,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"success": result.returncode == 0, "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def oc_apply_resource(yaml_content: str, namespace: str = "") -> dict[str, Any]:
    """Cria ou atualiza um recurso Kubernetes a partir de YAML."""
    args = ["apply", "-f", "-"]
    if namespace:
        args += ["-n", namespace]

    try:
        result = subprocess.run(
            get_oc_args(args),
            input=yaml_content,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"success": result.returncode == 0, "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def oc_delete_resource(resource: str, name: str, namespace: str = "",
                       ignore_not_found: bool = True) -> dict[str, Any]:
    """Remove um recurso Kubernetes."""
    args = ["delete", resource, name]
    if namespace:
        args += ["-n", namespace]
    if ignore_not_found:
        args += ["--ignore-not-found=true"]

    rc, out = run_oc(args)
    return {"success": rc == 0, "output": out, "error": None if rc == 0 else out}


def oc_get_json(resource: str, namespace: str = "", name: str = "") -> dict[str, Any]:
    """Obtem um recurso generico em JSON."""
    args = ["get"]
    if namespace and namespace != "ALL":
        args += ["-n", namespace]
    elif namespace == "ALL":
        args += ["-A"]

    args.append(resource)
    if name:
        args.append(name)
    args += ["-o", "json"]

    rc, out = run_oc(args)
    if rc != 0:
        return {"success": False, "output": "", "error": out}

    try:
        return {"success": True, "output": json.loads(out), "error": None}
    except json.JSONDecodeError:
        return {"success": False, "output": "", "error": f"Invalid JSON from oc: {out}"}


def sanitize_resource_for_apply(resource: dict[str, Any]) -> dict[str, Any]:
    """Remove campos gerenciados pelo apiserver antes de reaplicar o objeto."""
    cleaned = json.loads(json.dumps(resource))
    metadata = cleaned.setdefault("metadata", {})
    for key in (
        "annotations",
        "creationTimestamp",
        "deletionGracePeriodSeconds",
        "deletionTimestamp",
        "finalizers",
        "generation",
        "managedFields",
        "ownerReferences",
        "resourceVersion",
        "selfLink",
        "uid",
    ):
        metadata.pop(key, None)
    cleaned.pop("status", None)
    return cleaned


def find_dnspolicy_for_gateway(gateway: str, gateway_namespace: str) -> dict[str, Any]:
    """Procura uma DNSPolicy que aponte para o Gateway informado."""
    result = oc_get_json("dnspolicies.kuadrant.io", gateway_namespace)
    if not result.get("success", False):
        return result

    items = result.get("output", {}).get("items", [])
    for item in items:
        target_ref = item.get("spec", {}).get("targetRef", {})
        if target_ref.get("kind") == "Gateway" and target_ref.get("name") == gateway:
            return {
                "success": True,
                "output": item.get("metadata", {}).get("name", ""),
                "error": None,
            }

    return {"success": True, "output": "", "error": None}


def build_httproute_yaml(name: str, namespace: str, service: str, port: int,
                         gateway: str, gateway_namespace: str, hostname: str,
                         path_prefix: str) -> str:
    """Monta o YAML de uma HTTPRoute."""
    return f"""apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: {name}
  namespace: {namespace}
spec:
  parentRefs:
  - group: gateway.networking.k8s.io
    kind: Gateway
    name: {gateway}
    namespace: {gateway_namespace}
  hostnames:
  - "{hostname}"
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: {path_prefix}
    backendRefs:
    - kind: Service
      name: {service}
      port: {port}
"""


def resolve_hostname(hostname: str, dns_suffix: str, service: str) -> str:
    """Resolve o hostname final a partir do valor explicito ou sufixo DNS."""
    if hostname:
        return hostname

    if dns_suffix:
        normalized = dns_suffix.lstrip(".")
        return f"{service}.{normalized}"

    return ""


def build_dnspolicy_yaml(name: str, gateway: str, gateway_namespace: str,
                         health_check_path: str, health_check_port: int,
                         health_check_protocol: str) -> str:
    """Monta o YAML de uma DNSPolicy."""
    return f"""apiVersion: kuadrant.io/v1
kind: DNSPolicy
metadata:
  name: {name}
  namespace: {gateway_namespace}
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: Gateway
    name: {gateway}
  healthCheck:
    path: {health_check_path}
    port: {health_check_port}
    protocol: {health_check_protocol}
    failureThreshold: 3
    successThreshold: 1
"""


def build_httproute_rule(service: str, port: int, path_prefix: str) -> dict[str, Any]:
    """Monta uma regra padrao de HTTPRoute."""
    return {
        "matches": [
            {
                "path": {
                    "type": "PathPrefix",
                    "value": path_prefix,
                }
            }
        ],
        "backendRefs": [
            {
                "kind": "Service",
                "name": service,
                "port": port,
            }
        ],
    }


# --- MCP Tool handlers ---

def handle_list_gateways(params: dict) -> dict:
    """List all Gateways across all namespaces or in a specific namespace."""
    ns = params.get("namespace", "ALL")
    return oc_get_resource("gateway.networking.k8s.io", "v1", "Gateway", ns)


def handle_list_httproutes(params: dict) -> dict:
    """List all HTTPRoutes."""
    ns = params.get("namespace", "ALL")
    return oc_get_resource("gateway.networking.k8s.io", "v1", "HTTPRoute", ns)


def handle_list_authpolicies(params: dict) -> dict:
    """List all AuthPolicies."""
    ns = params.get("namespace", "ALL")
    return oc_get_resource("kuadrant.io", "v1", "AuthPolicy", ns)


def handle_list_ratelimitpolicies(params: dict) -> dict:
    """List all RateLimitPolicies."""
    ns = params.get("namespace", "ALL")
    return oc_get_resource("kuadrant.io", "v1", "RateLimitPolicy", ns)


def handle_list_dnspolicies(params: dict) -> dict:
    """List all DNSPolicies."""
    ns = params.get("namespace", "ALL")
    return oc_get_resource("kuadrant.io", "v1", "DNSPolicy", ns)


def handle_list_tlspolicies(params: dict) -> dict:
    """List all TLSPolicies."""
    ns = params.get("namespace", "ALL")
    return oc_get_resource("kuadrant.io", "v1", "TLSPolicy", ns)


def handle_get_gateway_status(params: dict) -> dict:
    """Get detailed status of a specific Gateway."""
    name = params.get("name", "")
    ns = params.get("namespace", "ALL")
    if not name:
        return {"success": False, "output": "", "error": "Gateway name required"}
    return oc_get_resource("gateway.networking.k8s.io", "v1", "Gateway", ns, name)


def handle_create_httproute(params: dict) -> dict:
    """Create or update an HTTPRoute to expose a service via a Gateway."""
    name = params.get("name", "")
    namespace = params.get("namespace", "")
    service = params.get("service", "")
    port = params.get("port", 8080)
    gateway = params.get("gateway", "rhcl-apps-gateway")
    gateway_namespace = params.get("gateway_namespace", "openshift-ingress")
    hostname = params.get("hostname", "")
    dns_suffix = params.get("dns_suffix", "")
    path_prefix = params.get("path_prefix", "/")

    if not all([name, namespace, service]):
        return {"success": False, "output": "",
                "error": "name, namespace, and service are required"}

    hostname = resolve_hostname(hostname, dns_suffix, service)
    if not hostname:
        return {
            "success": False,
            "output": "",
            "error": "hostname or dns_suffix is required for external exposure via RHCL",
        }

    yaml = build_httproute_yaml(
        name,
        namespace,
        service,
        port,
        gateway,
        gateway_namespace,
        hostname,
        path_prefix,
    )
    return oc_apply_resource(yaml, namespace)


def handle_create_dnspolicy(params: dict) -> dict:
    """Ensure a DNSPolicy exists for a Gateway."""
    gateway = params.get("gateway", "rhcl-apps-gateway")
    gateway_namespace = params.get("gateway_namespace", "openshift-ingress")
    name = params.get("name", f"{gateway}-dns")
    health_check_path = params.get("health_check_path", "/")
    health_check_port = params.get("health_check_port", 80)
    health_check_protocol = params.get("health_check_protocol", "HTTP")

    existing = find_dnspolicy_for_gateway(gateway, gateway_namespace)
    if not existing.get("success", False):
        return existing

    existing_name = existing.get("output", "")
    if existing_name:
        return {
            "success": True,
            "output": (
                f"DNSPolicy {existing_name} already exists for Gateway "
                f"{gateway} in namespace {gateway_namespace}\n"
            ),
            "error": None,
        }

    yaml = build_dnspolicy_yaml(
        name,
        gateway,
        gateway_namespace,
        health_check_path,
        health_check_port,
        health_check_protocol,
    )
    return oc_apply_resource(yaml, gateway_namespace)


def handle_patch_httproute(params: dict) -> dict:
    """Patch an existing HTTPRoute and converge it to the desired spec."""
    name = params.get("name", "")
    namespace = params.get("namespace", "")
    service = params.get("service", "")
    port = params.get("port", 8080)
    gateway = params.get("gateway", "")
    gateway_namespace = params.get("gateway_namespace", "")
    hostname = params.get("hostname", "")
    dns_suffix = params.get("dns_suffix", "")
    path_prefix = params.get("path_prefix", "/")

    if not all([name, namespace]):
        return {
            "success": False,
            "output": "",
            "error": "name and namespace are required",
        }

    route = oc_get_json("httproutes.gateway.networking.k8s.io", namespace, name)
    if not route.get("success", False):
        return route

    obj = sanitize_resource_for_apply(route.get("output", {}))
    spec = obj.setdefault("spec", {})

    resolved_hostname = resolve_hostname(hostname, dns_suffix, service)
    if resolved_hostname:
        spec["hostnames"] = [resolved_hostname]

    if gateway:
        parent_ref = {
            "group": "gateway.networking.k8s.io",
            "kind": "Gateway",
            "name": gateway,
        }
        if gateway_namespace:
            parent_ref["namespace"] = gateway_namespace
        spec["parentRefs"] = [parent_ref]

    if service:
        spec["rules"] = [build_httproute_rule(service, port, path_prefix)]

    yaml = json.dumps(obj)
    return oc_apply_resource(yaml, namespace)


def handle_delete_httproute(params: dict) -> dict:
    """Delete an existing HTTPRoute."""
    name = params.get("name", "")
    namespace = params.get("namespace", "")
    if not all([name, namespace]):
        return {
            "success": False,
            "output": "",
            "error": "name and namespace are required",
        }

    return oc_delete_resource(
        "httproutes.gateway.networking.k8s.io",
        name,
        namespace,
        ignore_not_found=True,
    )


def handle_expose_service(params: dict) -> dict:
    """Expose a Service via RHCL, ensuring HTTPRoute + DNSPolicy."""
    namespace = params.get("namespace", "")
    service = params.get("service", "")
    hostname = params.get("hostname", "")
    dns_suffix = params.get("dns_suffix", "")
    route_name = params.get("route_name", service)
    port = params.get("port", 8080)
    gateway = params.get("gateway", "rhcl-apps-gateway")
    gateway_namespace = params.get("gateway_namespace", "openshift-ingress")
    path_prefix = params.get("path_prefix", "/")
    ensure_dns_policy = params.get("ensure_dns_policy", True)
    dns_policy_name = params.get("dns_policy_name", f"{gateway}-dns")
    health_check_path = params.get("health_check_path", "/")
    health_check_port = params.get("health_check_port", 80)
    health_check_protocol = params.get("health_check_protocol", "HTTP")

    if not all([namespace, service]):
        return {
            "success": False,
            "output": "",
            "error": "namespace and service are required",
        }

    hostname = resolve_hostname(hostname, dns_suffix, service)
    if not hostname:
        return {
            "success": False,
            "output": "",
            "error": "hostname or dns_suffix is required",
        }

    route_lookup = oc_get_json("httproutes.gateway.networking.k8s.io", namespace, route_name)
    if route_lookup.get("success", False):
        route_result = handle_patch_httproute({
            "name": route_name,
            "namespace": namespace,
            "service": service,
            "port": port,
            "gateway": gateway,
            "gateway_namespace": gateway_namespace,
            "hostname": hostname,
            "path_prefix": path_prefix,
        })
    else:
        route_result = handle_create_httproute({
            "name": route_name,
            "namespace": namespace,
            "service": service,
            "port": port,
            "gateway": gateway,
            "gateway_namespace": gateway_namespace,
            "hostname": hostname,
            "path_prefix": path_prefix,
        })
    if not route_result.get("success", False):
        return route_result

    dns_summary = "DNSPolicy step skipped"
    if ensure_dns_policy:
        dns_result = handle_create_dnspolicy({
            "name": dns_policy_name,
            "gateway": gateway,
            "gateway_namespace": gateway_namespace,
            "health_check_path": health_check_path,
            "health_check_port": health_check_port,
            "health_check_protocol": health_check_protocol,
        })
        if not dns_result.get("success", False):
            return dns_result
        dns_summary = dns_result.get("output", "").strip()

    summary = (
        f"HTTPRoute {route_name} ensured in namespace {namespace}\n"
        f"Service: {service}:{port}\n"
        f"Gateway: {gateway} ({gateway_namespace})\n"
        f"Hostname: {hostname}\n"
        f"{dns_summary}\n"
    )
    return {"success": True, "output": summary, "error": None}


def handle_create_authpolicy(params: dict) -> dict:
    """Create an AuthPolicy to allow or deny access to a route."""
    name = params.get("name", "")
    namespace = params.get("namespace", "")
    route = params.get("route", "")
    allow = params.get("allow", True)

    if not all([name, namespace, route]):
        return {"success": False, "output": "",
                "error": "name, namespace, and route are required"}

    rego = "allow = true" if allow else "allow = false"
    yaml = f"""apiVersion: kuadrant.io/v1
kind: AuthPolicy
metadata:
  name: {name}
  namespace: {namespace}
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: {route}
  defaults:
    rules:
      authorization:
        {"allow-all" if allow else "deny-all"}:
          opa:
            rego: |
              {rego}
          priority: 1
    strategy: atomic
"""
    return oc_apply_resource(yaml, namespace)


# --- JSON-RPC handlers ---
tools_registry = {
    "list_gateways": {
        "description": "List all Gateway resources (Gateway API). "
                       "Accepts optional 'namespace' parameter. "
                       "Default: all namespaces.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace (or ALL for all namespaces)"
                }
            }
        },
        "handler": handle_list_gateways,
    },
    "list_httproutes": {
        "description": "List all HTTPRoute resources (Gateway API). "
                       "Accepts optional 'namespace' parameter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"}
            }
        },
        "handler": handle_list_httproutes,
    },
    "list_authpolicies": {
        "description": "List all AuthPolicy resources (Kuadrant API). "
                       "Accepts optional 'namespace' parameter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"}
            }
        },
        "handler": handle_list_authpolicies,
    },
    "list_ratelimitpolicies": {
        "description": "List all RateLimitPolicy resources (Kuadrant API).",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"}
            }
        },
        "handler": handle_list_ratelimitpolicies,
    },
    "list_dnspolicies": {
        "description": "List all DNSPolicy resources (Kuadrant API). "
                       "DNSPolicy is attached to a Gateway, not to an HTTPRoute.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"}
            }
        },
        "handler": handle_list_dnspolicies,
    },
    "list_tlspolicies": {
        "description": "List all TLSPolicy resources (Kuadrant API).",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"}
            }
        },
        "handler": handle_list_tlspolicies,
    },
    "get_gateway_status": {
        "description": "Get detailed status of a specific Gateway. "
                       "Requires 'name' parameter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "namespace": {"type": "string"}
            },
            "required": ["name"]
        },
        "handler": handle_get_gateway_status,
    },
    "create_httproute": {
        "description": "Create or update an HTTPRoute to expose a service via "
                       "the RHCL Gateway. External exposure requires a resolved "
                       "hostname, so provide hostname directly or provide "
                       "dns_suffix to generate <service>.<dns_suffix>. Prefer "
                       "expose_service when you want the application reachable "
                       "end-to-end.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "namespace": {"type": "string"},
                "service": {"type": "string"},
                "port": {"type": "integer"},
                "gateway": {"type": "string"},
                "gateway_namespace": {"type": "string"},
                "hostname": {"type": "string"},
                "dns_suffix": {"type": "string"},
                "path_prefix": {"type": "string"}
            },
            "required": ["name", "namespace", "service"]
        },
        "handler": handle_create_httproute,
    },
    "create_dnspolicy": {
        "description": "Ensure a DNSPolicy exists for a Gateway so hostnames "
                       "from HTTPRoutes can be published automatically. "
                       "Use this when exposing services externally via RHCL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "gateway": {"type": "string"},
                "gateway_namespace": {"type": "string"},
                "health_check_path": {"type": "string"},
                "health_check_port": {"type": "integer"},
                "health_check_protocol": {"type": "string"}
            }
        },
        "handler": handle_create_dnspolicy,
    },
    "patch_httproute": {
        "description": "Patch an existing HTTPRoute to converge hostname, "
                       "Gateway binding, backend service, port, and path. "
                       "Prefer this when the route already exists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "namespace": {"type": "string"},
                "service": {"type": "string"},
                "port": {"type": "integer"},
                "gateway": {"type": "string"},
                "gateway_namespace": {"type": "string"},
                "hostname": {"type": "string"},
                "dns_suffix": {"type": "string"},
                "path_prefix": {"type": "string"}
            },
            "required": ["name", "namespace"]
        },
        "handler": handle_patch_httproute,
    },
    "delete_httproute": {
        "description": "Delete an existing HTTPRoute. Safe to call when the "
                       "route may already be absent because it uses "
                       "ignore-not-found.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "namespace": {"type": "string"}
            },
            "required": ["name", "namespace"]
        },
        "handler": handle_delete_httproute,
    },
    "expose_service": {
        "description": "Preferred high-level tool to make an API reachable via "
                       "RHCL. It ensures the HTTPRoute has a hostname and ensures "
                       "a DNSPolicy exists on the target Gateway if needed. "
                       "Provide hostname directly or provide dns_suffix to "
                       "generate <service>.<dns_suffix> automatically. If the "
                       "HTTPRoute already exists, patch it instead of creating "
                       "a new one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
                "service": {"type": "string"},
                "hostname": {"type": "string"},
                "dns_suffix": {"type": "string"},
                "route_name": {"type": "string"},
                "port": {"type": "integer"},
                "gateway": {"type": "string"},
                "gateway_namespace": {"type": "string"},
                "path_prefix": {"type": "string"},
                "ensure_dns_policy": {"type": "boolean"},
                "dns_policy_name": {"type": "string"},
                "health_check_path": {"type": "string"},
                "health_check_port": {"type": "integer"},
                "health_check_protocol": {"type": "string"}
            },
            "required": ["namespace", "service"]
        },
        "handler": handle_expose_service,
    },
    "create_authpolicy": {
        "description": "Create an AuthPolicy for an HTTPRoute. "
                       "Requires: name, namespace, route. "
                       "Optional: allow (default true).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "namespace": {"type": "string"},
                "route": {"type": "string"},
                "allow": {"type": "boolean"}
            },
            "required": ["name", "namespace", "route"]
        },
        "handler": handle_create_authpolicy,
    },
}

SERVER_INFO = {
    "name": "rhcl-mcp-server",
    "version": "1.4.0",
    "description": "MCP Server for Red Hat Connectivity Link operations. "
                   "Provides tools to manage Gateways, HTTPRoutes, "
                   "DNSPolicy, AuthPolicies, and other RHCL resources.",
}


def handle_initialize(msg: dict) -> dict:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
            "resources": {},
            "prompts": {},
        },
        "serverInfo": SERVER_INFO,
    }


def handle_list_tools(msg: dict) -> dict:
    return {
        "tools": [
            {
                "name": name,
                "description": info["description"],
                "inputSchema": info["input_schema"],
            }
            for name, info in tools_registry.items()
        ]
    }


def handle_call_tool(msg: dict) -> dict:
    params = msg.get("params", {})
    name = params.get("name", "")
    arguments = params.get("arguments", {})

    tool = tools_registry.get(name)
    if not tool:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "isError": True,
        }

    try:
        result = tool["handler"](arguments)
        output = result.get("output", "")
        error = result.get("error", "")

        if result.get("success", False):
            return {"content": [{"type": "text", "text": output}]}
        else:
            return {
                "content": [{"type": "text", "text": error or output}],
                "isError": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": str(e)}],
            "isError": True,
        }


def main():
    import http.server
    import socketserver

    PORT = int(os.environ.get("MCP_PORT", "8080"))

    class MCPHandler(http.server.BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            # Reflete os headers pedidos no preflight (clientes MCP de browser
            # enviam mcp-protocol-version, mcp-session-id etc.)
            requested = self.headers.get("Access-Control-Request-Headers",
                                         "Content-Type, Authorization")
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", requested)
            self.send_header("Access-Control-Max-Age", "86400")
            self.end_headers()

        def do_DELETE(self):
            # Encerramento de sessao do Streamable HTTP (stateless aqui)
            self._respond(200, {"ok": True})

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"

            # Extrair token Bearer do header Authorization
            set_user_token("")
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                set_user_token(auth[7:])

            try:
                msg = json.loads(body)
            except json.JSONDecodeError:
                self._respond(400, {"error": "Invalid JSON"})
                return

            method = msg.get("method", "")
            msg_id = msg.get("id", None)

            # Notificacoes JSON-RPC (sem id) nao recebem resposta
            if method.startswith("notifications/") or msg_id is None:
                self.send_response(202)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return

            if method == "initialize":
                result = handle_initialize(msg)
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = handle_list_tools(msg)
            elif method == "tools/call":
                result = handle_call_tool(msg)
            else:
                result = {
                    "content": [{"type": "text",
                                 "text": f"Unknown method: {method}"}],
                    "isError": True,
                }

            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result,
            }
            self._respond(200, response)

        def do_GET(self):
            if self.path.rstrip("/") in ("/skill.md", "/skill"):
                try:
                    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "skill.md"), "rb") as f:
                        body = f.read()
                except OSError:
                    self._respond(404, {"error": "skill.md not found"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "name": SERVER_INFO["name"],
                "version": SERVER_INFO["version"],
                "tools": list(tools_registry.keys()),
                "skill": "/skill.md",
            }).encode())

        def _respond(self, status, data):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def log_message(self, format, *args):
            pass  # Suppress default HTTP logging

    with socketserver.TCPServer(("", PORT), MCPHandler) as httpd:
        print(f"RHCL MCP Server running on port {PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
