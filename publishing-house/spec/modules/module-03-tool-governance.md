# Module 3 — Round 2: Tool governance with MCP Gateway

**Module ID:** module-03
**Duration:** 22 min
**Platform layer:** Govern

**Anti-patterns addressed:**

| Anti-pattern | Description | Source |
|---|---|---|
| **Tool Overload** | Loading one agent with every available tool instead of scoping what it can see | Coyle / CCA — "specialize, don't overload" |
| **Description Collision** | Two tools whose free-text descriptions overlap enough that the model cannot reliably choose between them | Microsoft AI Red Team taxonomy v2.0 §4.8 *MCP / plugin abuse* and §4.3 *Agentic supply chain compromise*; OWASP ASI02 *Tool Misuse*, ASI04 *Supply Chain* |

### Brief Overview

The agent now calls tools, so it can now call the wrong one. Given an ambiguous customer request it selects a plausible-looking tool, gets a valid-looking result, and returns an answer that is wrong in a way nobody catches. The catalog exposes 18 tools to a single agent and two of them have descriptions that overlap.

Participants diagnose the collision from the trace, then put all tool access behind MCP Gateway so the agent sees only the tools its identity authorizes, and correct the two descriptions. The round closes with a prompt-injection attempt for a tool the agent's token does not permit, which the gateway refuses without ever reading the prompt.

The collision participants fix is accidental — two engineers wrote overlapping descriptions months apart. The literature describes the same mechanism as an attack. That is not a coincidence and the module says so directly: the reason a platform control is the right answer is that it fixes both cases identically, and the gateway cannot tell whether a description overlaps by accident or by design.

### Audience and Time

**Personas:** Technical Sellers and Services. Intermediate.

**Assumed on entry:** Participants completed Round 1, so the agent calls tools and terminates properly, and they can read a multi-turn trace. No prior MCP experience is assumed. Familiarity with tokens and claims is helpful but the round supplies what is needed.

**Duration:** 22 minutes — the longest round, because it carries both a diagnosis and two distinct fixes.

### Learning Objectives

- Analyze a trace to identify tool misselection and distinguish it from a tool that failed.
- Configure MCP Gateway so an agent is exposed only to the tools its identity authorizes.
- Implement corrected tool descriptions that a model can disambiguate reliably.
- Demonstrate why identity-based tool filtering at the gateway stops prompt-injection tool abuse that prompt-level instructions cannot.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | The wrong tool, confidently called | 4 min |
| 2 | Diagnosis — 18 tools and one collision | 5 min |
| 3 | Fix part 1 — put the catalog behind the gateway | 6 min |
| 4 | Fix part 2 — correct the colliding descriptions | 3 min |
| 5 | The injection attempt the gateway ignores | 4 min |
| — | **Total** | **22 min** |

### Detailed Steps

**Section 1 — The wrong tool (4 min)**

1. Run the agent against an ambiguous customer request, one that could plausibly route to either of two tools.
2. The agent returns a confident answer built on the wrong tool's output. The result is well-formed, which is why it survives review.
3. Note that nothing errored. No exception, no failed call, no warning.

**Section 2 — Diagnosis (5 min)**

4. Open the trace and identify which tool was actually invoked.
5. List the tools available to the agent. There are 18, all visible to one agent.
6. Compare the two candidate tool descriptions side by side. They overlap enough that the choice is close to arbitrary.
7. Name both anti-patterns here: **Tool Overload** (18 tools on one agent) and **Description Collision** (two of them indistinguishable).
8. Make the benign-versus-adversarial point explicitly. This collision was an accident. Microsoft's taxonomy describes the identical mechanism as an attack — a malicious server injecting natural-language instructions through tool descriptions that alter agent behaviour without touching any binary. Accidental and deliberate collisions are the same defect from the model's point of view, and the platform control fixes both without needing to tell them apart.

**Section 3 — Fix part 1, the gateway (6 min)**

9. Apply the supplied MCP Gateway configuration. The agent's tool access now runs through a single `MCP_URL` rather than direct server connections.
10. Apply the supplied agent identity and token claims.
11. Re-list the tools the agent can see. The catalog is now filtered by identity and has shrunk from 18 to the authorized subset. **This count is the section's success signal** — it is deterministic, verifiable per participant, and does not depend on the model choosing anything.
12. Do not re-run the request here. Both colliding tools remain authorized, so the ambiguity is unchanged and a re-run would show no improvement a participant could measure. The gateway reduced the blast radius; it did not fix the descriptions. Move to section 4.

**Section 4 — Fix part 2, the descriptions (3 min)**

13. Apply the supplied corrected descriptions for the two colliding tools. Each now states its purpose unambiguously and names what it is *not* for. The corrected pair also carries a schema change: the right tool requires a parameter the request supplies and the wrong tool does not accept, so the wrong tool cannot satisfy the request even if a model were to select it.
14. Confirm the fix by the schema, not the selection. The wrong tool now rejects the request outright, which is a deterministic check every participant sees identically. Re-run the ambiguous request as illustration — the correct tool should be selected — but the schema rejection is the proof.
15. Note the division of labour: the gateway is infrastructure and enforces what the agent may reach; the descriptions are content and determine what it chooses among what it may reach. Both are needed and they fail differently.

**Section 5 — The injection attempt (4 min)**

16. Submit the supplied prompt-injection request, crafted to talk the agent into calling a tool its token does not authorize.
17. The gateway refuses. Show in the trace that the tool never appeared in the agent's catalog, so there was nothing for the injection to talk it into.
18. Make the durable point: the gateway made no decision about the prompt. It never read it. Authorization happened at the infrastructure layer, on identity, before any prompt content was considered.
19. Contrast with the alternative participants have all seen — a system prompt saying "never call the refund tool for unverified customers" — and note that this is the same defect Round 4 attacks from the other direction.

### Key Takeaways

- An agent that calls the wrong tool produces no error. It produces a confident, well-formed, wrong answer.
- Tool descriptions are the model's only basis for choosing. Overlapping descriptions make the choice arbitrary, and free-text description fields have no schema validation to catch it.
- Accidental description collisions and deliberate tool poisoning are the same mechanism. The platform control fixes both, which is why it is the right layer for the fix.
- Identity-based filtering at the gateway defeats prompt injection because it never consults the prompt. A tool the token does not authorize is not in the catalog to be talked into.
- Scoping what an agent can see is a cheaper and more reliable control than trying to describe 18 tools well enough to disambiguate them.

### Infrastructure Notes

- Requires a pre-provisioned MCP server catalog exposing 18 tools, two of which carry deliberately overlapping descriptions. The collision must be planted and stable, not emergent.
- Requires MCP Gateway with per-identity token claims configured so that the filtered catalog is visibly shorter than the unfiltered one, and so that at least one tool is authorized for the injection target but excluded from this agent's identity.
- **The mechanic is verified end to end on 3.4.3, not merely assumed.** Behind one `MCP_URL` via a single `MCPVirtualServer`, a plain ServiceAccount's `tools/list` returned only the public tool while a second, privileged ServiceAccount additionally saw the admin tool — same URL, same session, different tool set purely by caller identity, with the caller's Kubernetes identity forwarded upstream via an `X-Auth-Request-User` header.
- **The provisioning burden is severe and must be pre-baked into the delivered environment, not performed in the room.** Reaching that working state took nine non-obvious steps, none discoverable from the CRD field documentation: the shared gateway only admits HTTPRoutes from two specific namespaces; Kuadrant, Authorino and Limitador are operators-only until a Kuadrant CR is created by hand; cross-namespace object references each need their own ReferenceGrant; `MCPGatewayExtension` needs `spec.publicHost` set explicitly; the session store needs a real Redis, not `memory://`, on a port the namespace NetworkPolicy actually admits; a further additive NetworkPolicy is needed for the broker's gRPC ext_proc port, without which every request hangs and 504s despite every CR reporting Ready; upstream MCP servers must implement `ping` or the broker silently drops all their tools; tools need an `id` field alongside `name`; and `MCPServerRegistration.userSpecificList` requires `spec.prefix`. Budget this as automation work, and treat it as evidence of what Tech Preview means in practice.
- **No load-bearing observable may depend on model choice.** Tool selection is stochastic in both directions and cannot be made deterministic by pinning temperature or seed, because vLLM's continuous batching means numerics vary with what else is in the batch — and a room hitting one shared endpoint concurrently guarantees a varying batch. The gateway's success signal is therefore the catalog count in section 3, and the corrected-description signal in section 4 must be a deterministic check: the corrected tool is the only one whose schema accepts a parameter the request requires, so the wrong tool cannot be called even if it were selected. The re-runs stay in the module as illustration, never as proof.
- The misselection in section 1 should still be biased hard — descriptions and input skewed so the wrong tool is the overwhelmingly likely choice — but the round must not break if a participant gets a lucky run.
- MCP Gateway is Tech Preview and Red Hat provided, verified as operator v0.7.1 on the dev cluster. **Status confirmed 2026-08-19** against primary documentation: Technology Preview via Red Hat Connectivity Link, and identity-based tool filtering is a capability of this component rather than of the Developer Preview MCP catalog in AI hub or the Developer Preview MCP lifecycle operator, neither of which this lab uses. Tech Preview is explicitly not covered by Red Hat production SLAs. Documented fallback if it regresses before the event: tool scoping at the MCP server or registry level plus RBAC — same principle, no gateway dependency.
- **Two distinct identity-filtering paths exist, and the module must commit to one.** Red Hat documents the gateway's filtering as an OAuth2 flow: Authorino validates the caller's token, extracts permissions from the identity provider, mints a cryptographically signed JWT "wristband" and injects it as an `x-authorized-tools` header, which the MCP Broker validates against a trusted public key before filtering the `tools/list` response. The dev-cluster verification took a different route — Kubernetes ServiceAccount identity forwarded upstream via `X-Auth-Request-User` with `MCPServerRegistration.userSpecificList`. Both filter by identity and both support the round's claim, but they differ in provisioning burden and in what the trace shows a participant. Decide during automation build which path the lab delivers, and make the module's screenshots and step text match it. The OAuth2/wristband path is the one Red Hat's own material describes, which matters for a module whose purpose is teaching the product's governance story.
- **The "never read the prompt" claim is architecturally exact, and worth keeping exact.** Filtering happens on the `tools/list` response, before any prompt content reaches the decision. That is why section 5's injection attempt fails, and it is a stronger claim than "the gateway blocked it" — nothing was blocked, because nothing was ever offered.
- Installing MCP Gateway pulls in Red Hat Connectivity Link, which is the productized Kuadrant, together with its Authorino and Limitador components. Round 4's authorization policy depends on these being present, so the two rounds share this provisioning.
- Participants arriving from Round 1 must have the correct model endpoint set. Add an entry assertion, and a "behind? run `lab reset --round 2`" callout, so a participant carrying a Round 1 defect does not misread it as a Round 2 failure.

- **Delivery model is self-paced.** Every instruction, warning and mitigation in this module must appear in participant-facing text. Steps written above as spoken direction — "note out loud", "ask participants", "say this out loud", "point out" — are cues for the separate facilitator guide, and each needs a participant-readable equivalent in the content so nothing depends on a facilitator speaking.

### References

- **Microsoft AI Red Team, "Taxonomy of Failure Modes in Agentic AI Systems", version 2.0** (whitepaper dated April 2026; announced June 2026), §4.8 *MCP / plugin abuse* and §4.3 *Agentic supply chain compromise*. Cross-references to OWASP ASI02 *Tool Misuse* and ASI04 *Supply Chain* are Microsoft's own, in §6.1.
- **OWASP GenAI Security Project — Top 10 for Agentic Applications (2026)**. Cite by name only until the primary document is read; the ASI numbering above is currently sourced through Microsoft's cross-reference.
- **Frank Coyle, "Anthropic's CCA Exam as a Field-Guide for Agentic Engineering"** (AI Engineer, August 2026) — "specialize, don't overload".
- Related catalog content, not a prerequisite: **Taking MCP Servers to Production on OpenShift AI with the Red Hat MCP Registry** (`published.openshift-mcp-lab.prod`), which covers tool filtering as least privilege at the registry level.
