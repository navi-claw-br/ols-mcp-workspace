# Operating RHCL via Lightspeed and the MCP Server

This document describes how OpenShift Lightspeed can help operate
Red Hat Connectivity Link using the integrated MCP Server.

## How it works

OpenShift Lightspeed has access to an MCP Server that can execute
commands on the OpenShift cluster using the logged-in user's permissions.

The MCP Server supports **any Kubernetes resource**, including CRDs such as:
- `gateway.networking.k8s.io/v1` - Gateway, HTTPRoute, GRPCRoute
- `kuadrant.io/v1` - AuthPolicy, RateLimitPolicy, DNSPolicy, TLSPolicy

Write operations must respect the logged-in user's RBAC. If the Lightspeed
response mentions the pod's service account (`system:serviceaccount:...`)
instead of the real user, that indicates a problem with token passthrough to the
custom MCP.

## Operational rules for exposing applications

When the user asks to expose, publish, or bring an API online via RHCL,
the expected behavior is autonomous:

1. ensure an `HTTPRoute` with a `hostname`
2. ensure a `DNSPolicy` on the `Gateway` if one does not exist yet
3. respond with the final FQDN and with what was changed

Important rules:

- never create an external `HTTPRoute` without `hostnames`
- for external exposure, the `hostname` is mandatory
- if the user does not provide an FQDN, generate one from `<service>.<dns_suffix>` when the environment's suffix is known
- `DNSPolicy` is attached to the `Gateway`, not to the `HTTPRoute`
- if a `DNSPolicy` already exists for the `Gateway`, reuse it
- prefer a single action that leaves the API working, rather than just generating YAML

### Preferred tool

When exposing a service, prefer the tool:

- `expose_service`

It must:

- create or update the `HTTPRoute`
- include the `hostname` or generate it from `dns_suffix`
- ensure a `DNSPolicy` on the `Gateway` when necessary
- return the final hostname

## Example prompts that work

### List RHCL resources

```
"List all Gateways in the cluster"
"Show me all HTTPRoutes"
"List AuthPolicies across all namespaces"
"What DNSPolicies exist?"
"Show TLSPolicies in openshift-ingress namespace"
"List RateLimitPolicies"
```

### Diagnose a Gateway

```
"Show the status of the rhcl-apps-gateway Gateway"
"Check if the Gateway is programmed"
"What's the ELB address for the gateway?"
"List all routes bound to rhcl-apps-gateway"
```

### Expose an application via RHCL

```
"Expose the rhcl-lab service via the rhcl-apps-gateway at rhcl-lab.poc.rhcl.com.br"
"Publish the debugocp service in debugocp3 at debugocp.poc.rhcl.com.br"
"Make my API reachable via RHCL and ensure DNS is published automatically"
"Create an AuthPolicy to allow access to my HTTPRoute"
"Configure TLS for my HTTPRoute"
```

### Check connectivity

```
"Check if the gateway has an ELB and is accepting traffic"
"List all pods in the tests namespace"
"Check the service my-app in tests namespace"
```

## Resources and their API groups

| Resource | API Group | Version |
|---|---|---|
| Gateway | gateway.networking.k8s.io | v1 |
| HTTPRoute | gateway.networking.k8s.io | v1 |
| GRPCRoute | gateway.networking.k8s.io | v1 |
| AuthPolicy | kuadrant.io | v1 |
| RateLimitPolicy | kuadrant.io | v1 |
| DNSPolicy | kuadrant.io | v1 |
| TLSPolicy | kuadrant.io | v1 |

## Useful commands (MCP)

When asking Lightspeed, use natural language:

- "List all Gateways" → MCP executes `oc get gateway -A`
- "Show HTTPRoutes in tests namespace" → `oc get httproute -n tests`
- "Describe the Gateway" → `oc describe gateway rhcl-apps-gateway -n openshift-ingress`
- "Expose service via RHCL" → MCP should prefer `expose_service`
- "Create HTTPRoute" → use only when the user asks for fine-grained control of the route
- "Remove HTTPRoute" → MCP should use `delete_httproute`
- "Ensure DNS publication" → MCP should check for or create a `DNSPolicy` on the Gateway
