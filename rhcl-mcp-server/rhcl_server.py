#!/usr/bin/env python3
"""RHCL MCP Server - Tools especializados para Red Hat Connectivity Link.

Este servidor MCP fornece tools especificas para operar o RHCL:
- Listar Gateways, HTTPRoutes, AuthPolicies
- Criar HTTPRoutes e AuthPolicies
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
    """Create an HTTPRoute to expose a service via a Gateway."""
    name = params.get("name", "")
    namespace = params.get("namespace", "")
    service = params.get("service", "")
    port = params.get("port", 8080)
    gateway = params.get("gateway", "rhcl-apps-gateway")
    gateway_namespace = params.get("gateway_namespace", "openshift-ingress")
    hostname = params.get("hostname", "")

    if not all([name, namespace, service]):
        return {"success": False, "output": "",
                "error": "name, namespace, and service are required"}

    yaml = f"""apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: {name}
  namespace: {namespace}
spec:
  parentRefs:
  - name: {gateway}
    namespace: {gateway_namespace}
"""
    if hostname:
        yaml += f"  hostnames:\n  - \"{hostname}\"\n"
    yaml += f"""  rules:
  - backendRefs:
    - name: {service}
      port: {port}
"""
    return oc_create_resource(yaml, namespace)


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
    return oc_create_resource(yaml, namespace)


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
        "description": "List all DNSPolicy resources (Kuadrant API).",
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
        "description": "Create an HTTPRoute to expose a service via "
                       "the RHCL Gateway. Requires: name, namespace, "
                       "service. Optional: port (default 8080), "
                       "gateway, gateway_namespace, hostname.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "namespace": {"type": "string"},
                "service": {"type": "string"},
                "port": {"type": "integer"},
                "gateway": {"type": "string"},
                "gateway_namespace": {"type": "string"},
                "hostname": {"type": "string"}
            },
            "required": ["name", "namespace", "service"]
        },
        "handler": handle_create_httproute,
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
    "version": "1.0.0",
    "description": "MCP Server for Red Hat Connectivity Link operations. "
                   "Provides tools to manage Gateways, HTTPRoutes, "
                   "AuthPolicies, and other RHCL resources.",
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
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()

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

            if method == "initialize":
                result = handle_initialize(msg)
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
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "name": SERVER_INFO["name"],
                "version": SERVER_INFO["version"],
                "tools": list(tools_registry.keys()),
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
