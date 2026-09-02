# Module 6. Connecting tools through the platform

### Brief Overview

Every tool the agent uses is currently wired point to point: the agent holds an address and a credential for each one, and nothing between them decides what the agent may reach. That is fine for one agent on one workbench and does not survive a second team, a second environment, or an audit question about who can call what.

Participants move tool access behind MCP Gateway, so the agent connects to one governed endpoint and receives the tools its identity authorizes. The failure this module opens with is not a crash: it is a working agent whose reach nobody can describe.

This module is deliberately supporting rather than load-bearing. The neighbouring Agents, Security/Governance lab owns identity-aware authorization in depth, and this design stops at the build step.

### Audience and Time

Technical Sellers and Services, intermediate. 12 minutes.

Requires module 5, or at least a working agent with more than one tool registered.

### Learning Objectives

- Configure tool access through MCP Gateway so the agent reaches its tools by a governed path rather than by direct connection.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Describe what the agent can reach | 3 min |
| 2 | Point the agent at the gateway | 5 min |
| 3 | See the governed catalog | 3 min |
| 4 | What this makes possible later | 1 min |

### Detailed Steps

1. Inspect the agent's current tool configuration. Each tool carries its own address and its own credential, held by the agent.
2. Answer, from the configuration alone, the question an auditor would ask: what is the complete set of things this agent can reach? Note that answering requires reading the agent's code, and that the answer changes whenever someone edits it.
3. Note the second problem: every environment needs its own copy of that configuration, and they drift.
4. Replace the per-tool configuration with a single gateway endpoint and the supplied identity credential.
5. Re-run a question from an earlier module and confirm the agent still works. Nothing about its behaviour should change.
6. Request the tool list the gateway serves for this identity. Confirm it matches what the agent actually used.
7. Note that the catalog is now a property of the platform and the identity, not of the agent's source code. The auditor's question is answerable without reading the agent.
8. Confirm in the trace that tool invocations now route through the gateway.
9. Name what this enables and stop there: the same mechanism that filters this catalog by identity is what allows a different identity to be given a different set of tools, which is where the governance lab picks up.

### Key Takeaways

- Point-to-point tool wiring works and is unauditable. The agent's reach is whatever its code currently says.
- A governed endpoint makes the tool catalog a platform property, so it can be described, versioned and changed without touching agent code.
- Moving to the gateway should be behaviour-neutral. If the agent behaves differently afterwards, something was wrong before.
- Filtering the catalog by identity happens before the model sees it, so a tool the identity does not hold is not something the model can be talked into calling.

### Infrastructure Notes

- **MCP Gateway is Tech Preview**, delivered via Red Hat Connectivity Link, verified as operator v0.7.1 on the dev cluster on 2026-08-18. Tech Preview is not covered by Red Hat production SLAs.
- **Documented fallback.** If it regresses before the event, tool scoping at the MCP server or registry level plus RBAC demonstrates the same principle without the gateway. This module carries one learning objective and no assessed outcome that fails without it, which is the reason the redesign moved governance here rather than keeping it as a full round.
- **The provisioning burden is severe and must be pre-baked.** Reaching a working identity-filtered catalog on the dev cluster took nine non-obvious steps, none discoverable from CRD field documentation: the shared gateway only admits HTTPRoutes from specific namespaces; Kuadrant, Authorino and Limitador are operators-only until a Kuadrant CR is created by hand; each cross-namespace reference needs its own ReferenceGrant; `MCPGatewayExtension` needs `spec.publicHost` set explicitly; the session store needs a real Redis, not `memory://`, on a port the NetworkPolicy admits; a further additive NetworkPolicy is needed for the broker's gRPC ext_proc port, without which every request hangs and 504s while every CR reports Ready; upstream MCP servers must implement `ping` or the broker silently drops their tools; tools need an `id` alongside `name`; and `MCPServerRegistration.userSpecificList` requires `spec.prefix`. Budget this as automation work. None of it happens in the room.
- **Two identity-filtering paths exist and the build must commit to one.** Red Hat documents an OAuth2 flow where Authorino validates the caller's token, extracts permissions from the identity provider, mints a signed JWT and injects it as an `x-authorized-tools` header, which the MCP Broker validates against a trusted public key to filter `tools/list`. Dev-cluster verification instead used Kubernetes ServiceAccount identity forwarded upstream as `X-Auth-Request-User` with `MCPServerRegistration.userSpecificList`. Both filter by identity. They differ in provisioning burden and in what a participant sees. The OAuth2 path is the one Red Hat's own material describes.
- **Verified end to end on 3.4.3.** Behind one `MCP_URL` via a single `MCPVirtualServer`, a plain ServiceAccount's `tools/list` returned only the public tool while a privileged ServiceAccount additionally saw the admin tool. Same URL, same session, different tool set purely by caller identity.
- **Scope discipline.** No prompt-injection exercise, no adversarial testing, no policy authoring. Those belong to the Security/Governance lab and were the substance of the overlap that got the previous design rejected.
