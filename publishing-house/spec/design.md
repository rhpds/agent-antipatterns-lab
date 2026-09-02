# Building an Agent on OpenShift AI: Each Step, and How It Breaks First

## Topic Alignment

This design replaces a version rejected at content review on 2026-09-01 for overlapping the Agents, Security/Governance slot. The rejection was correct: the previous four rounds covered tool governance, observability and policy enforcement, which is the neighbouring lab's subject, not this one's.

This slot asks for "this is how you build an agent", the prerequisite before governance. So the lab now builds an agent rather than governing an inherited one. Governance appears once, in module 6, as the way tools get connected on the platform, and carries no learning objective of its own. Adversarial scanning and policy enforcement are gone.

Three other candidate labs sit in this slot, and all three consume a hosted or centrally served model, LB1782 states outright that participants "consume a centrally-hosted, pre-deployed Granite model". None of them configures a serving runtime. That is the gap this design leads with, and it is the one part of the rejected version that carried no overlap with anything.

## Overview

Most agent tutorials build something that works on the demo input and leave the participant with no idea why it breaks the first time it meets a real one. This lab builds a multi-step agent on Red Hat OpenShift AI one layer at a time, and opens every layer with that layer failing.

Participants build the agent themselves. In each module they add a capability, run it against a realistic input, watch it fail in a way that produces no error and no obvious symptom, find the cause in the request and response payloads on the inference endpoint, and then build the step that prevents it. The rule the lab runs on is established in module 1 and holds throughout: the agent's answer is a claim, the wire is the evidence.

The order is forced by dependency rather than preference. A model that cannot emit a parseable tool call makes every later layer untestable. A loop that never terminates makes error handling unobservable. Error handling has to be honest before retrieval is worth adding, because otherwise a search that returns nothing reads as an answer. Governance only means something once the agent is genuinely reaching tools.

## Target Audience

- **Role:** Technical Sellers and Services, solution architects, consultants, and delivery engineers who build or advise on agent solutions with customers.
- **Experience level:** Intermediate
- **What they already know:** What an LLM agent is, conceptually. Comfortable with the OpenShift web console and basic `oc` operations. Able to read Python and modify supplied code.
- **What they don't know:** That model serving configuration, not prompt quality, decides whether tool calls happen at all; that a loop which does not read the model's stop condition will repeat itself indefinitely; that a tool returning a well-formed empty result is indistinguishable from success unless the contract makes it distinguishable.

## Prerequisites

- Working knowledge of the OpenShift web console and basic `oc` operations (log in, switch project, read a pod log).
- Familiarity with LLM agents at a conceptual level. Having built one is helpful and not required.
- Ability to read Python and edit supplied code. Participants modify a working file rather than writing from scratch.
- No prior experience with vLLM, MCP, or vector search is required. Each is introduced in the module that uses it.
- **Can the lab validate these automatically?** No. This is a classic Showroom lab with no solve/validate automation, so prerequisites are trust-based and stated in the introduction rather than machine-checked.

## Learning Objectives

1. Deploy a vLLM serving runtime on OpenShift AI configured so that a model's tool calls are emitted and parsed rather than stranded as text in the response body.
2. Analyze the request and response payloads on an inference endpoint to determine whether a tool call was emitted, parsed, or silently discarded.
3. Troubleshoot an agent that never calls a tool by comparing the endpoint's serving arguments against the tool-call format the model was trained to produce.
4. Build an agent loop that terminates on the model's reported stop condition rather than on a text heuristic, a first response, or an iteration cap.
5. Implement a structured tool-error contract of category, retryable flag and detail so that failed tool calls surface instead of becoming confident empty answers.
6. Integrate a searchable knowledge source so the agent grounds its answers in retrieved content rather than in model memory.
7. Configure tool access through MCP Gateway so the agent reaches its tools by a governed path rather than by direct connection.
8. Verify the assembled agent end to end against the failure cases from every earlier step before treating it as more than a prototype.

## Content Type

Lab (hands-on), delivered self-paced.

**Delivery model.** Participant-facing content stands alone. Every instruction, warning and recovery step lives in text a participant reads, so nothing breaks for someone working ahead of the room or recovering from a failed step. A short facilitator guide carries the discussion beats that benefit from a person present, the framing in module 1 and the customer-conversation work in module 7, but no step depends on a facilitator speaking for its outcome to be correct.

## Products & Technologies

- **Red Hat OpenShift AI 3.4 or later**, the platform for the whole lab. Validated during development on 3.4.3. Components exercised:
  - vLLM model serving via **Red Hat AI Inference Server**, module 2, and the endpoint every later module runs against
  - **MLflow Tracing**, module 1 as the instrument, module 7 as the verification record
  - **MCP Gateway**, module 6
- **Red Hat OpenShift Container Platform 4.20 or later**, underlying platform
- **Red Hat Connectivity Link** (Kuadrant, Authorino), installed as a dependency of MCP Gateway
- Upstream projects: vLLM, Model Context Protocol, MLflow, OpenTelemetry
- Vector store for module 5, selection open, see Infrastructure Requirements
- Model: `RedHatAI/Qwen3-8B-FP8-dynamic`, Red Hat validated. The serving recipe follows Red Hat's documented Qwen reference configuration for the KServe vLLM runtime:

  ```
  --dtype=auto --max-model-len=32768 --enable-auto-tool-choice \
  --tool-call-parser=hermes --reasoning-parser=qwen3 --gpu-memory-utilization=0.90
  ```

  **`--reasoning-parser=qwen3` is not optional and must be identical on both endpoints.** Red Hat documents a known issue where Qwen3 models emit raw tags when the correct reasoning parser is unavailable. That is a second silent tool-calling failure sitting next to the one module 2 plants, presenting a similar symptom from a different cause. If it differs between the two endpoints, a participant can diagnose the wrong fault and still appear to be right. The only permitted difference is the `--tool-call-parser` value.

**Component maturity.** These are delivery commitments. Two statuses are given: what was observed against 3.4.x during development, and what has to hold at Red Hat One in February 2027.

| Component | At validation (3.4.x) | Expected at event | Note |
|---|---|---|---|
| vLLM model serving | GA | GA | Core to Red Hat AI |
| vLLM tool-calling configuration | Documented serving-runtime arguments, not preview on this path | Same | Resolved 2026-08-19. Standalone Red Hat AI Inference Server carries a Developer Preview notice on tool calling, and it scopes the whole feature rather than one parser — the same boilerplate appears in the Qwen 3 chapter and the gpt-oss chapter. That notice does not govern this lab. On RHOAI/KServe these are ordinary vLLM arguments passed via *Additional serving runtime arguments*, documented in GA deployment procedures with no preview caveat. Stated precisely, that is the absence of a preview label rather than an affirmative support statement. Recommend the infra reviewer confirm with the RHOAI product team. |
| MLflow (incl. Tracing) | GA since OpenShift AI 3.4 | GA | Traces are OpenTelemetry-compatible, so any OTEL sink can back the lab |
| MCP Gateway | Tech Preview via Red Hat Connectivity Link | Tech Preview, GA not announced | Operator v0.7.1, verified installed on the dev cluster 2026-08-18. Now supporting rather than load-bearing: module 6 carries no learning objective that fails without it. Documented fallback if it regresses, tool scoping at the MCP server or registry level plus RBAC. |
| Vector store (module 5) | Not yet selected | To be confirmed | The one genuinely open item in this design. See Infrastructure Requirements. |

Guardrails Orchestrator, NeMo Guardrails, EvalHub and Garak were all in the rejected version and are all removed. That takes both Tech Preview dependencies off the critical path.

## Module Map

| Module | Title | Duration | Opens with | Closes with |
|---|---|---|---|---|
| 1 | What you are building, and how to see inside it | 12 min | A confident answer built from nothing | Reading the wire and the first trace |
| 2 | The model interface: making tool calls fire at all | 22 min | Tools declared, none ever called, no error | A serving runtime whose parser matches the model |
| 3 | The agent loop: stop conditions and turn control | 16 min | The same tool called until the iteration cap | Termination on the model's reported stop condition |
| 4 | Tool returns that tell the truth | 16 min | A well-formed empty result read as success | A structured error contract |
| 5 | Giving the agent knowledge it can search | 14 min | A plausible answer from model memory | Answers grounded in retrieved content |
| 6 | Connecting tools through the platform | 12 min | Point-to-point wiring with nothing governing reach | Tool access through MCP Gateway |
| 7 | Running it for real: verification and field positioning | 13 min | Every layer passing alone, none checked together | Every earlier failure case re-run against the whole |
| — | **Total content** | **105 min** | | |
| — | Reserve for room settle, mass login, transitions and overrun | 15 min | | |
| — | **Total slot** | **2 hours** | | |

The schedule budgets 105 minutes into a 120-minute slot deliberately. Every conference session loses time at the front to logistics, and this lab's single mass-login event sits in module 1.

Module 2 carries the most time because it is the layer no other candidate in this slot teaches, and because its diagnosis is the hardest in the lab: the model emitted a correct tool call, the parser did not match it, and the call was left in the response body as text with nothing raising an error.

**Known tension, flagged for content review.** Module 7 carries both end-to-end verification and the customer-conversation work in 13 minutes, and that is tight. In the earlier design the positioning segment was protected from compression because it is the artifact a Technical Seller takes back to a customer. If review agrees it is too thin, the cleanest correction is moving four minutes from module 2 rather than shortening the reserve.

## Difficulty Level

Intermediate

## Environment

**Learner view:** Each participant starts with a pre-provisioned OpenShift AI workbench holding a partially built agent: tool definitions, a stub loop, and a supplied test input. Nothing in it works end to end at the start, and that is the point. Two shared class-wide endpoints serve the same model, one with a deliberately mismatched tool-call parser and one with the validated recipe, and the participant's agent starts pointed at the broken one. Also pre-deployed: an MCP server exposing the lab's tools, an MLflow tracking server reachable by Route, and a populated vector store for module 5.

**Automation needed:** Yes

Automation must provision the workbench per participant with the agent repo pre-cloned; both shared endpoints; the MCP server and its tool definitions; MCP Gateway with per-identity token claims; the MLflow tracking server and Route; the vector store with its corpus already ingested; and a reset path that returns any module to its starting state.

**Provisioning findings from dev-cluster verification (RHOAI 3.4.3):**

- **MCP Gateway is the heaviest item by a wide margin.** Reaching a working identity-filtered catalog took nine non-obvious manual steps, none discoverable from CRD field documentation: gateway namespace admission rules, a hand-created Kuadrant CR, ReferenceGrants for cross-namespace references, an explicit `publicHost`, a real Redis session store on a NetworkPolicy-permitted port, an additive NetworkPolicy for the broker's gRPC ext_proc port, a `ping` method on upstream servers, an `id` field on tools, and a required `spec.prefix`. All of it must be pre-baked. This is a large part of why module 6 is now 12 minutes and supporting rather than a full round.
- **MLflow is a cluster-wide singleton.** The CR must be named `mlflow` and always lands in `redhat-ods-applications` regardless of where it is created, so no per-participant tracking server is possible. This forces the shared-cluster topology.
- **Identity filtering has two documented paths and the build must pick one.** Red Hat documents an OAuth2 flow where Authorino validates the token, mints a signed JWT and injects it as an `x-authorized-tools` header which the MCP Broker uses to filter `tools/list`. Dev-cluster verification used Kubernetes ServiceAccount identity forwarded as `X-Auth-Request-User` with `MCPServerRegistration.userSpecificList`. Both work and they differ in provisioning burden.

**Authoring constraints carried into the modules:**

- The agent must be **non-streaming**. Upstream vLLM issue #31871 reports the hermes tool-call parser returning raw text instead of parsed `tool_calls` in streaming mode, which is the exact symptom module 2 teaches, occurring as a live bug even when configuration is correct. A streaming agent would make the documented fix appear not to work.
- Module 1 must document the MLflow authentication workaround. Known issue RHOAIENG-44516: Kubernetes tokens are not accepted through the OpenShift AI Gateway, so a direct Route is used as `MLFLOW_TRACKING_URI`. Known issue RHOAIENG-45969: artifact serving backed by S3 is not configured by the automatic workbench integration.
- **Every planted failure must be structural**, a mismatched parser, a loop that discards its stop condition, an unstructured tool return, an empty retrieval result, and never dependent on the model choosing to misbehave. Stochastic failures will not reproduce identically across a room, and vLLM's continuous batching means numerics vary with whatever else is in the batch.

## Infrastructure Requirements

- **Platform:** OpenShift, with Red Hat OpenShift AI
- **Cloud provider:** AWS. Chosen over the CNV default because the lab needs a GPU with native FP8 compute, which is an instance-type question AWS answers directly.
- **Cluster type:** Multinode
- **OCP version:** 4.20 minimum. Dev-cluster validation ran on 4.21.21 with RHOAI 3.4.x.
- **Topology:** Shared cluster. Forced rather than preferred: MLflow is a cluster-wide singleton, so a per-participant tracking server is not possible, and module 1 depends on one. The two shared endpoints point the same way.
- **Sizing:**
  - Control plane: 3 × 16 vCPU / 64 GB RAM
  - Workers: 6 × 16 vCPU / 64 GB RAM / 200 GB disk, carrying 30 workbenches plus MCP Gateway and its Redis session store, the MLflow tracking server, the MCP server, and the vector store. Sized with roughly 35% headroom deliberately: dev-cluster experience showed pods failing to schedule on a node that was mostly idle because requests were over-reserved relative to use.
  - Planning cap: **30 concurrent participants**
- **Automation approach:** GitOps (Helm + ArgoCD), with `bootstrap-tenant` for per-user namespace and RBAC under the shared-cluster topology
- **AI/MaaS:** **GPU, not MaaS.** 1 GPU node, 4 × NVIDIA L40S 48 GB (AWS g6e.12xlarge). Model `RedHatAI/Qwen3-8B-FP8-dynamic`, open-source tier.

  MaaS cannot satisfy this lab. Module 2's mechanic is comparing two serving configurations of the same model, and a hosted chat API exposes no serving configuration, so the module would have no failure to diagnose. This is also what separates the design from the other candidates in the slot, all of which consume a centrally hosted model.

  L40S rather than A100 is a hard requirement. The model is an FP8 checkpoint, and native FP8 compute requires compute capability 8.9 or later, meaning Ada Lovelace or Hopper. On Ampere vLLM does not fail; it silently falls back to weight-only W8A16 via FP8 Marlin, dequantizing to 16-bit before the tensor cores. That gives the memory saving and none of the FP8 throughput, which would be an indefensible trace in a lab whose subject is serving configuration.

  Four GPUs map one vLLM instance per GPU: the broken endpoint on GPU 0, three replicas of the validated endpoint on GPUs 1 to 3. This avoids per-instance `gpu_memory_utilization` fractions entirely and keeps the failure domain per endpoint. After module 2 the whole room repoints to the validated endpoint, so peak concurrent generation lands there. Published benchmarks show Qwen3-8B sustaining a sweep to 256 concurrent requests on a single A10G with no dropped requests; L40S is materially faster with native FP8, so 30 participants across three replicas carries substantial headroom. Keep `--max-model-len` at the documented 32768 rather than maximal, since single-GPU throughput degrades under concurrency at very long context lengths.
- **Vector store:** open. Module 5 needs a searchable corpus and nothing more exotic. The selection should favour whatever RHOAI already ships or GitOps can stand up without a new operator dependency, and it should be sized for a read-only corpus ingested at provisioning time rather than written during the lab. Flagged for the infra reviewer.
- **External services:** `registry.redhat.io` (RHOAI and operator images), `quay.io` (workbench and MCP server images), `huggingface.co` (model weights, unless pre-staged into cluster storage at provisioning), `github.com` (the agent repo cloned into each workbench), `pypi.org` (Python dependencies). The environment is not air-gapped.
- **AAP version:** Not applicable. Ansible Automation Platform is not in the product list.
- **Non-GA products:** One. **MCP Gateway**, Tech Preview via Red Hat Connectivity Link. It ships inside RHOAI and the normal operator catalog, so no separate entitlement or non-standard registry is needed. It is no longer load-bearing: module 6 teaches governed tool access as a build step, and if the gateway regresses before the event the documented fallback is tool scoping at the MCP server or registry level plus RBAC, which demonstrates the same principle. No learning objective fails without it.

## Assessment Strategy (Optional)

Trust-based, stated explicitly. This is a classic Showroom lab with no solve/validate automation, so completion is not machine-verified. Each module instead ends in a visible, unambiguous result the participant confirms, chosen so it does not depend on the model choosing correctly.

| Module | Observable success signal |
|---|---|
| 1 | The agent returns an answer, and the participant locates the corresponding request, response and trace. |
| 2 | `tool_calls` changes from empty, with tool-call text stranded in the response content, to populated. The agent invokes a tool. |
| 3 | The run terminates on the model's stop condition rather than the iteration cap, verifiable by a turn count well below the cap. |
| 4 | The swallowed failure re-runs as a structured, categorized error instead of a confident empty answer. |
| 5 | The same question that previously produced a plausible invention now returns an answer traceable to a retrieved passage, and a question outside the corpus returns an explicit miss rather than an invention. |
| 6 | The tool list the agent can reach is served through the gateway, and a tool outside its identity's authorization does not appear. |
| 7 | Every earlier failure case re-run against the assembled agent produces the corrected behaviour. No machine-verifiable signal for the positioning segment, which produces a takeaway artifact. |
