# Module 6. Connecting tools through the platform

### Brief Overview

Every tool the agent uses is currently hardcoded: the agent holds an address and a credential for each one. That works, and it means adding a tool is an application change. Someone edits the agent, rebuilds it, and redeploys it, and every environment needs its own copy of that configuration.

Participants point the agent at MCP Gateway instead, so it discovers its tools at runtime from one endpoint. A tool is then registered at the gateway and the agent picks it up with no code change, no rebuild and no restart. The failure this module opens with is not a crash. It is a build that has coupled tool changes to release cycles.

### Audience and Time

Technical Sellers and Services, intermediate. 10 minutes.

Requires module 3, or any working agent with more than one tool registered.

### Learning Objectives

- Configure an agent to reach its tools through MCP Gateway so that tools can be added or changed without modifying or redeploying the agent.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Count the cost of adding a tool | 2 min |
| 2 | Point the agent at the gateway | 4 min |
| 3 | Add a tool without touching the agent | 4 min |

### Detailed Steps

1. Inspect the agent's current tool configuration. Each tool carries its own address and its own credential, written into the agent.
2. Work out what adding a new tool costs today: edit the agent, rebuild the image, redeploy, and repeat that in every environment the agent runs in. Tool changes are application releases.
3. Replace the per-tool configuration with a single gateway endpoint.
4. Re-run a question from an earlier module. Confirm the agent still behaves identically. Moving to the gateway should change nothing about what the agent does.
5. Request the tool list the gateway serves. Confirm it matches the tools the agent had before, and note that the agent is now discovering them at runtime rather than carrying them.
6. Register the supplied `estimate_delivery` tool at the gateway. This is a platform operation and touches nothing in the agent.
7. Without editing the agent, rebuilding it, or restarting it, ask: *"If we ship that pump from Denver to the customer site in Boulder, when does it arrive?"* Answering requires `estimate_delivery`.
8. Confirm the agent discovered and used a tool it did not have two minutes ago. **This is the module's success signal, and it is a visible new capability rather than an absence.**
9. Note what this changes about deployment: the tool catalog became a property of the platform, versioned and changed independently of the agent's release cycle.

### Key Takeaways

- Hardcoded tool wiring couples every tool change to an application release, which is invisible with one tool and painful with twenty.
- A gateway makes the tool catalog a runtime property, so tools can be added, replaced or rolled back without shipping the agent.
- Moving to the gateway should be behaviour-neutral. If the agent behaves differently afterwards, something was wrong before.
- The same endpoint is where access control is applied later. This lab stops at connection.

### Infrastructure Notes

- **Scope discipline, and this is the module's most important constraint.** No identity, no per-caller tool filtering, no authorization, no prompt-injection exercise, no policy authoring. An earlier version of this design taught identity-filtered catalogs here and was rejected for overlapping the neighbouring Agents Security/Governance lab, which owns that ground in depth with two personas. Section 3's payoff must stay "a tool appeared without a redeploy", never "a tool was hidden from someone". Reframed 2026-09-02.
- **The success signal must be a visible addition, not an absence.** The previous version asked participants to confirm that an unauthorized tool did not appear in their catalog, which is unobservable: they hold one identity and are never shown the unfiltered list. Adding a tool and watching it arrive is observable by one participant with one credential.
- **The added tool must be genuinely usable in-room.** Registering it has to be a single supplied command or manifest, and the question that exercises it must be unambiguous, so the 4-minute section holds.
- **The agent must pick up the new tool without a restart.** If the agent caches its tool list at startup, section 3 fails and the module has no payoff. Confirm refresh behaviour during authoring and, if a refresh is needed, make it an explicit step rather than a hidden one.
- **MCP Gateway is Tech Preview**, delivered via Red Hat Connectivity Link, verified as operator v0.7.1 on the dev cluster on 2026-08-18. Tech Preview is not covered by Red Hat production SLAs. Documented fallback if it regresses before the event: an MCP server or registry fronting the tools plus RBAC, which still demonstrates runtime tool discovery without the gateway. This module carries one objective and no assessed outcome elsewhere in the lab depends on it.
- **Provisioning burden, reduced but still real.** Reaching a working gateway on the dev cluster took nine non-obvious steps, none discoverable from CRD field documentation: gateway namespace admission rules, a hand-created Kuadrant CR, ReferenceGrants for cross-namespace references, an explicit `spec.publicHost`, a real Redis session store on a NetworkPolicy-permitted port, an additive NetworkPolicy for the broker's gRPC ext_proc port, a `ping` method on upstream servers, an `id` field on tools, and `spec.prefix` on `MCPServerRegistration`. All of it must be pre-baked. Dropping identity filtering removes the per-identity token claims and `userSpecificList` configuration, and with them the open question of which identity-filtering path to build. That question is now moot rather than deferred.
- **Known in-room failure mode.** Misconfigured, the broker hangs and returns 504s while every CR reports Ready. With 30 concurrent sessions this is the most fragile component in the lab, which is a further reason the module is short and carries nothing else.
- **Verified on 3.4.3.** Behind one `MCP_URL` via a single `MCPVirtualServer`, tools registered at the gateway were served to a calling ServiceAccount. The same verification also showed per-identity filtering working, which is a real capability of the component and is deliberately not taught here.
- **Agent identity is a different axis and is deliberately absent.** This module is about how an agent reaches its tools. It is not about the agent's own cryptographic identity, meaning who the agent claims to be when another agent calls it. That axis, A2A Agent Cards, SPIFFE and SPIRE workload binding and signed cards, now lands in OpenShell, named in the Red Hat AI agentic strategy as the unified agent security and lifecycle project with an operator planned for RHOAI 3.6. The neighbouring Security/Governance lab is built on OpenShell and lists SPIFFE and SPIRE in its product set. Checked 2026-09-02: no Kagenti, SPIRE or A2A component exists in any catalog source on the dev cluster.
- **Two other assets touch MCP and were checked on 2026-09-02.** The published *vLLM Playground* lab has an MCP integration module, and `showroom-agentic-ai-llamastack` has a dedicated MCP module. Both connect an agent to MCP servers. This module's distinct claim is narrower: not that MCP exists or how to connect to a server, but that routing tool access through the platform decouples tool changes from agent releases.
