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
- Model: `RedHatAI/Qwen3-8B-FP8-dynamic` — Red Hat validated (model card states validation on RHOAI 2.24 / RHAIIS 3.2.1). The validated serving recipe follows Red Hat's own documented Qwen reference configuration for the KServe vLLM runtime:

  ```
  --dtype=auto --max-model-len=32768 --enable-auto-tool-choice \
  --tool-call-parser=hermes --reasoning-parser=qwen3 --gpu-memory-utilization=0.90
  ```

  Two points carry into the build. **`--reasoning-parser=qwen3` is not optional.** Red Hat documents a known issue where Qwen3 models emit raw tags when the correct reasoning parser is unavailable — a second silent tool-calling failure sitting directly beside the one Round 1 plants. Omitting it risks a participant diagnosing the wrong fault, so it belongs in the validated endpoint and must not be what distinguishes the broken endpoint from the working one. **`--gpu-memory-utilization=0.90` is the documented default and is retained unchanged**, which the one-instance-per-GPU layout makes possible; co-scheduling instances on a shared device would have forced invented per-instance fractions instead.

**Component maturity.** These are delivery commitments and RHDP will hold the lab to them, so the table gives two statuses: what was observed against 3.4.x during development, and what has to hold when the lab runs at Red Hat One in February 2027. On the release cadence observed to date, RHOAI will have shipped at least one further release by then; the exact version is an assumption to confirm, not a commitment.

| Component | At validation (3.4.x) | Expected at event (Feb 2027) | Note |
|---|---|---|---|
| vLLM model serving | GA | GA | Core to Red Hat AI |
| vLLM tool-calling configuration | **Documented serving-runtime arguments — not preview on this path** | Same | **Resolved 2026-08-19.** The contested reading splits by delivery vehicle, and both halves were right. Standalone RHAIIS *does* carry a Developer Preview notice on tool calling, and it scopes the whole feature rather than one parser — the identical boilerplate appears in the Qwen 3 chapter and the gpt-oss chapter of "Extending Red Hat AI Inference with tool calling capabilities." That notice does not govern this lab: the lab serves through RHOAI/KServe, where `--enable-auto-tool-choice` and `--tool-call-parser` are ordinary vLLM arguments passed via *Additional serving runtime arguments* on the vLLM NVIDIA GPU ServingRuntime, documented in GA deployment procedures with no preview caveat. Stated precisely, this is the *absence* of a preview caveat rather than the *presence* of an affirmative support statement — Red Hat documents the flags in GA procedures but publishes no "tool calling is supported" commitment. Recommend the infra reviewer confirm with the RHOAI product team. |
| MCP Gateway | Tech Preview, Red Hat provided | **Tech Preview — GA not announced** | **Confirmed 2026-08-19.** Technology Preview via Red Hat Connectivity Link; operator v0.7.1 verified installed on the dev cluster 2026-08-18. Round 2's identity-based tool filtering belongs to this component, not to a separate one — Authorino validates the OAuth2 token, extracts permissions from the identity provider, mints a signed JWT "wristband" and injects it as an `x-authorized-tools` header, which the MCP Broker validates against a trusted public key to filter the `tools/list` response. The MCP catalog in AI hub and the MCP lifecycle operator are the Developer Preview pieces; this lab depends on neither. Fallback if it regresses: tool scoping at the MCP server/registry level plus RBAC — same principle, no gateway dependency. |
| MLflow (incl. Tracing) | GA since OpenShift AI 3.4 | GA | Delivered via the MLflow Operator. Traces are OpenTelemetry-compatible; any OTEL sink can back the lab if needed |
| TrustyAI Guardrails Orchestrator | GA since OpenShift AI 2.19 | GA | No mitigation required. Note that what reached Tech Preview in 3.0 was the Llama Stack integration, not the orchestrator itself |
| NeMo Guardrails | GA since OpenShift AI 3.4 | GA | Deploys via the TrustyAI Operator as a single CR; no NVIDIA subscription required |
| Garak, EvalHub | Tech Preview as of 3.4 | **Tech Preview — GA not expected** | **Resolved 2026-08-19, and the answer is worse than assumed.** EvalHub is not GA in 3.4 and is not GA in 3.5: the client SDK/CLI and the Evaluation Stack UI are Technology Preview in both releases, and no GA date is announced. Garak's own tier is ambiguous — Technology Preview as an EvalHub provider, but described as developer preview in OpenShift AI 3.4 in Red Hat blog material. A distribution rename is also in flight: the Garak provider ships in the Llama Stack distribution in 3.4 and in the OGX distribution in 3.5. This lab reaches Garak through the TrustyAI EvalHub CR rather than that distribution, which is why it worked on the dev cluster with `llamastackoperator` set to Removed, but the vehicle is moving underneath the lab and needs re-verification against whatever ships at the event. Verified installing and running on 3.4.3: a single-probe benchmark returned an Attack Success Rate in about 11 seconds end to end. **Author decision 2026-08-19: Garak remains Round 4's verification instrument, with Tech Preview status disclosed to participants.** (3.5 notes consulted were Early Access, so final GA text could still shift.) |

**Maturity resolution status.** All three open rows were settled against primary Red Hat documentation on 2026-08-19. Two resolved more favourably than the design assumed — the Developer Preview notice on tool calling does not govern the RHOAI/KServe path this lab uses, and MCP Gateway's Tech Preview status is confirmed with its identity-filtering mechanism documented. One resolved less favourably: EvalHub and Garak remain Technology Preview across two consecutive releases with no announced GA, and Round 4 keeps them on its critical path by author decision, with the status disclosed rather than mitigated. The one item still open is not a maturity question but a support question — whether Red Hat will affirmatively state that vLLM tool calling is supported on KServe, as distinct from merely documenting it without caveat. That is for the infra reviewer to take up with the RHOAI product team.

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

- **Platform:** OpenShift (OCP) — Red Hat OpenShift AI is the base for all four rounds
- **Cloud provider:** AWS — chosen over the CNV default because the lab requires a GPU with native FP8 compute, which is an instance-type question AWS answers directly
- **Cluster type:** Multinode
- **OCP version:** 4.20 minimum. Dev-cluster validation ran on 4.21.21 with RHOAI 3.4.x
- **Topology:** **Shared-cluster.** This is forced rather than preferred. MLflow is a cluster-wide singleton — the CR must be named `mlflow` and always lands in `redhat-ods-applications` regardless of where it is created — so a per-participant tracking server is not possible, and Round 3 depends on one. The two shared class-wide model endpoints point the same way.
- **Sizing:**
  - Control plane: 3 × 16 vCPU / 64 GB RAM
  - Workers: 6 × 16 vCPU / 64 GB RAM / 200 GB disk — carrying 30 participant workbenches plus MCP Gateway and its Redis session store, the MLflow tracking server, the Guardrails Orchestrator, EvalHub, and the 18-tool MCP server catalog. Sized with roughly 35% headroom on purpose: dev-cluster experience showed pods failing to schedule on a node that was mostly idle, because requests were over-reserved relative to actual use.
  - Planning cap: **30 concurrent participants**
- **Automation approach:** GitOps (Helm + ArgoCD), with `bootstrap-tenant` included for per-user namespace and RBAC under the shared-cluster topology
- **AI/MaaS:** **GPU, not MaaS** — 1 GPU node, 4 × NVIDIA L40S 48 GB (AWS g6e.12xlarge: 4 GPUs, 48 vCPU, 384 GB RAM). Model `RedHatAI/Qwen3-8B-FP8-dynamic`, open-source tier.

  MaaS cannot satisfy this lab. Round 1's mechanic is switching the agent between two serving configurations of the same model, and a hosted chat API exposes no serving configuration — the round would have no failure to diagnose.

  L40S rather than A100 is a hard requirement, not a preference. The model is an FP8 checkpoint, and native FP8 compute (W8A8) requires compute capability 8.9 or later — Ada Lovelace or Hopper. On Ampere, vLLM does not fail; it silently falls back to weight-only W8A16 via FP8 Marlin, dequantizing to 16-bit before the tensor cores. That delivers the memory saving and none of the FP8 throughput, which would be an indefensible trace in a lab whose subject is serving configuration.

  Four GPUs resolve the co-scheduling problem the proposal review raised. Rather than fitting multiple instances onto one device with explicit `gpu_memory_utilization` fractions, each vLLM instance gets its own GPU: the broken endpoint on GPU 0, three replicas of the validated endpoint on GPUs 1–3. This delivers the design's "third replica of the validated endpoint" intent — the broken endpoint is dead weight from Round 1 onward, and GPU 0 is repurposable once the room has converged — while keeping the failure domain per-endpoint.

  On throughput, which is the real question rather than memory: published benchmarks show Qwen3-8B sustaining a concurrency sweep to 256 simultaneous requests on a single A10G with zero dropped requests and median TTFT around 524 ms. L40S is materially faster and adds native FP8, so 30 concurrent participants spread across three validated replicas carries substantial headroom. One constraint carries into the build — keep `--max-model-len` bounded rather than maximal, since single-GPU concurrency degradation under long context lengths is a reported vLLM behaviour.
- **External services:** `registry.redhat.io` (RHOAI and operator images), `quay.io` (workbench and MCP server images), `huggingface.co` (Qwen3-8B-FP8-dynamic weights, unless pre-staged into cluster storage during provisioning), `github.com` (the inherited agent prototype repo, cloned into each workbench), `pypi.org` (Python dependencies for the agent, MCP servers and MLflow client). The environment is not air-gapped.
- **AAP version:** Not applicable — Ansible Automation Platform is not in the product list for this lab
- **Non-GA products:** Three pre-GA dependencies as of validation — the vLLM tool-calling configuration (Developer Preview, and itself unconfirmed; see the maturity table), MCP Gateway (Tech Preview), and EvalHub with the Garak provider (Tech Preview as of 3.4). MLflow, NeMo Guardrails and the TrustyAI Guardrails Orchestrator are all GA and are not pre-GA dependencies.

  **Access plan:** all three ship inside RHOAI 3.4+ and the TrustyAI operator, so provisioning installs them through the normal operator catalog — no separate entitlement, early-access programme or non-standard registry. Two carry documented fallbacks if maturity regresses before the event: tool scoping at the MCP server/registry level plus RBAC in place of MCP Gateway, and any OpenTelemetry-compatible sink in place of MLflow. Garak via EvalHub is load-bearing for Round 4 verification and has no equivalent fallback, so its GA timing must be settled against the RHOAI release notes before submission.

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
