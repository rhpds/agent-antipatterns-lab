# Four Ways Your Agent Fails in Production — and the Red Hat AI Feature That Fixes Each

## Overview

The gap between an agent prototype that impresses in a meeting and a system that survives production is where enterprise agent projects die — and the failures are consistent across every framework and every vendor. This lab uses four of those failure modes as the entry point to four Red Hat AI capabilities, one for each platform layer: serve, govern, observe, enforce. Across the four rounds it names and sources seven distinct anti-patterns, since several of the rounds carry more than one.

Participants inherit a working agent prototype that is about to ship. In each of four rounds they run the agent against a realistic input, watch it fail plausibly, diagnose the cause from an execution trace, and then apply a supplied configuration to a named Red Hat AI component to fix it. Round 1 redeploys the model endpoint with a validated tool-calling configuration and corrects the agent's stop-condition handling. Round 2 puts all tool access behind MCP Gateway with identity-based filtering. Round 3 instruments the agent with MLflow Tracing to find an error the agent reported as a success, and applies a structured error contract. Round 4 moves a compliance rule out of the system prompt into the TrustyAI Guardrails Orchestrator and a gateway authorization policy. Diagnosis is the reasoning work; remediation is guided, so participants finish each round having used the product to address an agentic development anti-pattern.

## Target Audience

- **Role:** Technical Sellers and Services — solution architects, consultants, and delivery engineers who position or implement agent solutions with customers.
- **Experience level:** Intermediate
- **What they already know:** What an LLM agent is and how one is structured; they have built or demoed at least one. Comfortable with the OpenShift web console and basic `oc` CLI operations. Able to read Python.
- **What they don't know:** The platform-layer contract that keeps agents working in production — why model serving configuration (not prompt quality) determines whether tool calls are emitted, how gateway-enforced tool authorization defeats prompt injection, how to diagnose from a trace instead of from the final answer, and why compliance rules must be enforced outside the model.

## Prerequisites

- Working knowledge of the OpenShift web console and basic `oc` CLI operations (log in, switch project, view a pod log).
- Familiarity with LLM agents at a conceptual level — having built or demoed one is sufficient.
- Ability to read Python. No requirement to write it beyond applying supplied configuration.
- No prior experience with vLLM, MCP, MLflow, or TrustyAI is required — each is introduced in the round that uses it.
- **Can the lab validate these automatically?** No. This is a classic Showroom lab with no solve/validate automation, so prerequisites are trust-based and stated in the lab introduction rather than machine-checked.

## Learning Objectives

1. Analyze an OpenShift AI execution trace to diagnose an agent's runtime behavior rather than judging it by its final output.
2. Troubleshoot a model endpoint's tool-calling configuration from an execution trace, and explain why a mismatched chat template or tool parser causes an agent to silently never call tools.
3. Configure an agent loop to inspect the model's stop condition rather than trusting the first response or parsing text for a completion signal.
4. Configure MCP Gateway so an agent is exposed only to the tools its identity authorizes, and demonstrate why this stops prompt-injection tool abuse at the infrastructure layer.
5. Monitor an agent with MLflow Tracing and use it to locate a failure that the agent reported as a success.
6. Implement a structured tool-error contract (error category, retryable flag, detail) so that silent tool failures surface instead of becoming confident, empty answers.
7. Migrate a compliance-critical business rule out of a system prompt into the TrustyAI Guardrails Orchestrator and gateway authorization policy.
8. Demonstrate the four failure modes and the corresponding Red Hat AI feature in a customer conversation.

## Content Type

Lab (hands-on), delivered self-paced.

**Delivery model.** Participant-facing content must stand completely alone. Every instruction, warning and risk mitigation lives in text a participant reads, so nothing breaks for someone working ahead of the room or recovering from a failed step. A separate, short facilitator guide carries the discussion beats that benefit from a person in the room — the framing in Module 1, the "what would you change first" moment in Round 1, and the customer-conversation work in Module 6 — but no step depends on a facilitator speaking for its outcome to be correct.

## Products & Technologies

- **Red Hat OpenShift AI 3.4 or later** — the platform for all four rounds. 3.4 is the minimum, being the release where MLflow and NeMo Guardrails reached GA. Validated during development on 3.4.3. The delivered version will be whatever is current at the event, which on the cadence observed to date will be at least one release beyond 3.4. Components exercised:
  - vLLM model serving via **Red Hat AI Inference Server** — Round 1
  - **MCP Gateway** — Round 2
  - **MLflow Tracing** — Round 3
  - **TrustyAI Guardrails Orchestrator** — Round 4
  - **EvalHub**, with the **Garak** adversarial-scanning provider — Round 4 verification
- **Red Hat OpenShift Container Platform 4.x** — underlying platform
- **Red Hat Connectivity Link** (Kuadrant AuthPolicy, Authorino) — gateway authorization in Round 4; installed as a dependency of MCP Gateway
- Upstream projects: vLLM, Model Context Protocol (MCP), MLflow, OpenTelemetry
- Model: `RedHatAI/Qwen3-8B-FP8-dynamic` — Red Hat validated (model card states validation on RHOAI 2.24 / RHAIIS 3.2.1), served with `--enable-auto-tool-choice --tool-call-parser hermes`

**Component maturity.** These are delivery commitments and RHDP will hold the lab to them, so the table gives two statuses: what was observed against 3.4.x during development, and what has to hold when the lab runs at Red Hat One in February 2027. On the release cadence observed to date, RHOAI will have shipped at least one further release by then; the exact version is an assumption to confirm, not a commitment.

| Component | At validation (3.4.x) | Expected at event (Feb 2027) | Note |
|---|---|---|---|
| vLLM model serving | GA | GA | Core to Red Hat AI |
| vLLM tool-calling configuration | **Developer Preview — to be verified** | **To be confirmed** | Recorded as Developer Preview on the basis that the "Extending Red Hat AI Inference Server with tool calling capabilities" guide carries a Developer Preview notice, and Developer Preview features are not Red Hat supported. That reading is contested and needs checking against the guide's front matter: the Developer Preview label in the RHAIIS 3.4 release notes attaches to distributed inference with llm-d, and Red Hat's own enablement material uses these flags without preview caveats. Round 1 depends on this capability, so the claim must be settled before submission — it is currently the most conservative reading, not a confirmed one. |
| MCP Gateway | Tech Preview, Red Hat provided | To be confirmed — TP or better | Operator v0.7.1, verified installed on the dev cluster 2026-08-18. Fallback if it regresses: tool scoping at the MCP server/registry level plus RBAC — same principle, no gateway dependency. |
| MLflow (incl. Tracing) | GA since OpenShift AI 3.4 | GA | Delivered via the MLflow Operator. Traces are OpenTelemetry-compatible; any OTEL sink can back the lab if needed |
| TrustyAI Guardrails Orchestrator | GA since OpenShift AI 2.19 | GA | No mitigation required. Note that what reached Tech Preview in 3.0 was the Llama Stack integration, not the orchestrator itself |
| NeMo Guardrails | GA since OpenShift AI 3.4 | GA | Deploys via the TrustyAI Operator as a single CR; no NVIDIA subscription required |
| Garak, EvalHub | Tech Preview as of 3.4 | **To be confirmed** | Round 4 has adopted Garak via EvalHub as its verification instrument, so this row is load-bearing. GA timing is not publicly announced; the maturity commitment for the event is tracked separately and must be settled before submission. Verified installing and running on 3.4.3: a single-probe benchmark returned an Attack Success Rate in about 11 seconds end to end. |

Every "to be confirmed" above needs resolving against the RHOAI release notes before submission. None of them blocks the design, but none can be asserted without a primary source either.

## Module Map

| Module | Title | Duration |
|--------|-------|----------|
| 1 | Meet the prototype | 15 min |
| 2 | Round 1 — Loop discipline and tool-calling configuration | 20 min |
| 3 | Round 2 — Tool governance with MCP Gateway | 22 min |
| 4 | Round 3 — Observability with MLflow Tracing | 18 min |
| 5 | Round 4 — Enforcement with Guardrails Orchestrator | 15 min |
| — | **Total hands-on** | **90 min** |
| — | Field wrap and positioning (module 6, discussion) | 15 min |
| — | **Total content** | **105 min** |
| — | Reserve for room settle, mass login, transitions and overrun | 15 min |
| — | **Total slot** | **2 hours** |

The schedule deliberately budgets 105 minutes of content into a 120-minute slot. Every conference session loses time at the front to logistics before a word of content, and this lab's single mass-login event sits in Module 1. Module 6 is protected from compression because it carries the customer-conversation script, which is the one artifact a Technical Seller takes back to a customer.

Each round follows the same rhythm: the agent fails plausibly, participants diagnose from the trace, then apply a supplied configuration to a named component. The order is forced by dependency. A model that cannot call tools has to be fixed before tool routing matters, tool routing has to work before error visibility matters, and enforcement only means anything once the agent is taking actions. Module 1 teaches the trace-reading that every later round depends on.

## Difficulty Level

Intermediate

## Environment

**Learner view:** Each participant starts with a pre-provisioned OpenShift AI workbench containing the inherited agent prototype — a working, non-streaming Python agent with its tool definitions and loop code. Two shared, class-wide model endpoints of the same model are already serving: one deliberately configured with a mismatched tool-call parser, and one with the validated recipe. The broken endpoint sets `--enable-auto-tool-choice` with a parser that does not match the model, which fails silently — tool-call text is left in the response content and `tool_calls` stays empty. Omitting the flags entirely would not work, because vLLM rejects such a request with HTTP 400 rather than producing the confident wrong answer the round depends on. The participant's agent starts pointed at the broken endpoint. Also pre-deployed: an MCP server catalog exposing 18 tools (two of them with colliding descriptions, planted for Round 2), an MLflow tracking server reachable by Route, and a Guardrails Orchestrator instance. Running the agent against the demo input succeeds; running it against a realistic input fails.

**Automation needed:** Yes

Automation must provision: the OpenShift AI workbench per participant with the prototype repo pre-cloned; both shared model endpoints (broken and validated) on the shared GPU; the MCP server catalog and its 18 tool definitions including the planted description collision; MCP Gateway with per-identity token claims; the MLflow tracking server plus an OpenShift Route to it; the TrustyAI Guardrails Orchestrator and the Kuadrant AuthPolicy used in Round 4; EvalHub with the Garak provider and RBAC for the evaluation job in Round 4; and the per-round "broken" starting state so every participant begins each round from an identical, deterministic failure.

**Provisioning findings from dev-cluster verification (RHOAI 3.4.3):**

- **MCP Gateway is the heaviest item by a wide margin.** Reaching a working identity-filtered catalog took nine non-obvious manual steps, none of them discoverable from CRD field documentation — gateway namespace admission rules, a hand-created Kuadrant CR, ReferenceGrants for cross-namespace references, an explicit `publicHost`, a real Redis session store on a NetworkPolicy-permitted port, an additive NetworkPolicy for the broker's gRPC ext_proc port, a `ping` method on upstream servers, an `id` field on tools, and a required `spec.prefix`. All of it must be pre-baked; none of it can happen in the room.
- **MLflow is a cluster-wide singleton.** The CR must be named `mlflow` and always lands in `redhat-ods-applications` regardless of where it is created, so no per-participant tracking server is possible. This constrains the topology choice in Phase 5.
- **EvalHub and Garak install cleanly** through the TrustyAI operator with no configuration beyond a normal EvalHub CR, and a single-probe Garak benchmark returned an Attack Success Rate in about 11 seconds end to end.
- **GuardrailsOrchestrator requires a real KServe ServingRuntime**, so Round 4's enforcement path cannot be validated until Round 1's model serving is working. This is a sequencing dependency for the build, not a design flaw.

**Authoring constraints carried into the modules:**

- The agent must be built **non-streaming**. Upstream vLLM issue #31871 reports the hermes tool-call parser returning raw text instead of parsed `tool_calls` in streaming mode — the exact symptom Round 1 teaches, occurring as a live bug even when configuration is correct. A streaming agent would make the documented fix appear not to work.
- Round 3 must document the MLflow authentication workaround. Known issue RHOAIENG-44516: Kubernetes tokens are not accepted through the OpenShift AI Gateway, so service accounts cannot authenticate via the dashboard MLflow URL. The module instructs participants to use a direct OpenShift Route as `MLFLOW_TRACKING_URI`. Known issue RHOAIENG-45969: MLflow artifact serving backed by S3 is not configured by the automatic workbench integration — parameters, metrics and tags log correctly, but `log_artifact()` requires manual setup.
- Every planted failure must be structural — broken loop code, colliding tool descriptions, a misconfigured gateway, an unstructured error return — and never dependent on the model choosing to misbehave. Stochastic failures would not reproduce identically across a room.

## Infrastructure Requirements

- **Cloud provider:** TBD — confirmed in infrastructure phase
- **Cluster type:** TBD — confirmed in infrastructure phase
- **OCP version:** TBD — confirmed in infrastructure phase
- **Topology:** TBD — confirmed in infrastructure phase
- **Sizing:** TBD — confirmed in infrastructure phase
- **Automation approach:** TBD — confirmed in infrastructure phase
- **AI/MaaS:** TBD — confirmed in infrastructure phase. Open question carried from proposal review: Round 1's mechanic requires two serving configurations of the same model, which rules out a closed hosted chat API for that round. Proposed approach is two shared class endpoints on a single GPU. Note that the "~9GB each at FP8" figure counts model weights only — it excludes KV cache, and vLLM reserves `gpu_memory_utilization` (0.9 by default) of the device per instance, so co-scheduling two instances needs explicit per-instance memory fractions. The sizing question is also throughput, not just memory: after Round 1 the whole room repoints to the validated endpoint, so peak concurrent generation lands on a single instance. Requires an RHDP answer on GPU availability, framed as a throughput question rather than a memory one. Planning cap is **30 concurrent participants**. Provisioning should also stand up a **third replica of the validated endpoint**: the broken endpoint is dead weight from Round 1 onward, so that capacity is better spent serving the configuration the whole room converges on.
- **External services:** TBD — confirmed in infrastructure phase
- **AAP version:** Not applicable — Ansible Automation Platform is not in the product list for this lab
- **Non-GA products:** TBD — confirmed in infrastructure phase. The pre-GA dependencies as of validation are the vLLM tool-calling configuration (Developer Preview, and itself unconfirmed — see the maturity table), MCP Gateway (Tech Preview), and EvalHub with the Garak provider (Tech Preview as of 3.4). MLflow, NeMo Guardrails and the TrustyAI Guardrails Orchestrator are all GA and are not pre-GA dependencies.

## Assessment Strategy (Optional)

Trust-based, stated explicitly. This is a classic Showroom lab with no solve/validate automation to author, so completion is not machine-verified. Each round instead ends in a visible, unambiguous result the participant confirms for themselves:

| Module | Observable success signal |
|---|---|
| 1 | The agent runs green on the demo input and red on the realistic input; the participant has the first trace open. |
| 2 (Beat A) | `tool_calls` changes from empty, with tool-call text stranded in the response content, to populated — the agent invokes a tool. |
| 2 (Beat B) | The run terminates on the model's own stop condition rather than the iteration cap, verifiable by the turn count ending well below the cap. |
| 3 | The tool catalog visible to the agent shrinks from 18 to the identity-authorized subset, and a prompt-injection attempt for an unauthorized tool is refused by the gateway. |
| 4 | The swallowed error is located in the trace, and the re-run surfaces it as a structured, categorized failure instead of a confident empty answer. |
| 5 | The adversarial set that previously breached the prompt-based rule is now blocked, with the guardrail returning a blocked verdict for every case. |
| 6 | No machine-verifiable signal. Module 6 is discussion-led and produces a takeaway artifact rather than a system state. |
