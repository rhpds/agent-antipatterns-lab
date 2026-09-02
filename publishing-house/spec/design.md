# Building an Agent on OpenShift AI: Each Step, and How It Breaks First

## Topic Alignment

This design replaces a version rejected at content review on 2026-09-01 for overlapping the Agents, Security/Governance slot. The rejection was correct: the previous four rounds covered tool governance, observability and policy enforcement, which is the neighbouring lab's subject, not this one's.

This slot asks for "this is how you build an agent", the prerequisite before governance. So the lab now builds an agent rather than governing an inherited one. Governance does not appear. Module 6 uses MCP Gateway purely as the way tools get connected, so tool changes stop being application releases, and it teaches no identity, filtering or authorization. Adversarial scanning and policy enforcement are gone.

Three other candidate labs sit in this slot, and all three consume a hosted or centrally served model, LB1782 states outright that participants "consume a centrally-hosted, pre-deployed Granite model". None of them configures a serving runtime. That is the gap this design leads with, and it is the one part of the rejected version that carried no overlap with anything.

## Strategic Alignment

Red Hat AI's agentic strategy names five themes. This lab sits on two of them, quoting the strategy document directly:

> **Self-Hosted Inference That Works for Agents:** Make vLLM reliable for agentic workloads, specifically tool calling, multi-turn reasoning, and code execution, so customers stop defaulting to frontier APIs.

> **Deploying/Managing Your First Agent on Red Hat:** Provide a Day 0 to Day 2 onboarding path with starter kits, templates, playground, and integrated docs.

The same document states the stakes plainly: "If open-weight models on vLLM cannot reliably handle agentic tool calling, customers default to frontier APIs, and the sovereignty and open-source value propositions collapse." Module 2 is that problem in a room, which is the strongest argument for why this lab leads with serving configuration rather than treating it as setup.

**Where agent identity sits, and why it is not here.** Agent identity is moving quickly: A2A Agent Cards, SPIFFE and SPIRE workload binding, and signed cards. That work now lands in **OpenShell**, which the strategy names as the unified agent security and lifecycle project, with an operator planned for RHOAI 3.6 handling identity injection. The neighbouring Agents Security/Governance lab is built on OpenShell and lists SPIFFE and SPIRE in its product set. Adopting agent cards here would rebuild the overlap that got the previous design rejected.

This design teaches neither axis. Module 6 stops at **how an agent reaches its tools**, so that adding a tool is a platform operation rather than an application release. Caller identity deciding which tools are visible, and agent identity establishing who the agent is to other agents, both belong to the neighbouring lab. Neither Kagenti, SPIRE nor any A2A component is present in the dev cluster's catalogs today.

## Overview

Most agent tutorials build something that works on the demo input and leave the participant with no idea why it breaks the first time it meets a real one. This lab builds a multi-step agent on Red Hat OpenShift AI one layer at a time, and opens every layer with that layer failing.

Participants build the agent themselves. In each module they add a capability, run it against a realistic input, watch it fail in a way that produces no error and no obvious symptom, find the cause in the request and response payloads on the inference endpoint, and then build the step that prevents it. The rule the lab runs on is established in module 1 and holds throughout: the agent's answer is a claim, the wire is the evidence.

The order is forced by dependency rather than preference. A model that cannot emit a parseable tool call makes every later layer untestable. A loop that never terminates makes error handling unobservable. Error handling has to be honest before retrieval is worth adding, because otherwise a search that returns nothing reads as an answer. Module 6 comes late because decoupling tool changes from agent releases only matters once there are several tools worth changing, and module 7 can only verify an agent that is fully assembled.

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
7. Configure an agent to reach its tools through MCP Gateway so that tools can be added or changed without modifying or redeploying the agent.
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
- **PostgreSQL with the pgvector extension** for module 5, deployed as a plain Deployment via GitOps
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
| MCP Gateway | Tech Preview via Red Hat Connectivity Link | Tech Preview, GA not announced | Operator v0.7.1, verified installed on the dev cluster 2026-08-18. Now supporting rather than load-bearing: module 6 teaches runtime tool discovery, and the documented fallback demonstrates the same thing without the gateway. Documented fallback if it regresses, tool scoping at the MCP server or registry level plus RBAC. |
| PostgreSQL with pgvector (module 5) | GA, deployed directly | GA | Settled 2026-09-02. Red Hat OpenShift AI is standardizing on pgvector as a remote vector store provider, so this is the platform's direction rather than an arbitrary pick. The RHOAI built-in pgvector provider integration is EA2 as of 3.5 and is deliberately not used: the retrieval tool queries Postgres directly, which needs nothing pre-GA and stays forward-compatible with that integration when it GAs. |

Guardrails Orchestrator, NeMo Guardrails, EvalHub and Garak were all in the rejected version and are all removed. That takes both Tech Preview dependencies off the critical path.

## Module Map

| Module | Title | Duration | Opens with | Closes with |
|---|---|---|---|---|
| 1 | What you are building, and how to see inside it | 12 min | A confident answer built from nothing | Reading the wire and the first trace |
| 2 | The model interface: making tool calls fire at all | 22 min | Tools declared, none ever called, no error | A serving runtime whose parser matches the model |
| 3 | The agent loop: stop conditions and turn control | 16 min | The same tool called until the iteration cap | Termination on the model's reported stop condition |
| 4 | Tool returns that tell the truth | 14 min | A well-formed empty result read as success | A structured error contract |
| 5 | Giving the agent knowledge it can search | 14 min | A plausible answer from model memory | Answers grounded in retrieved content |
| 6 | Connecting tools through the platform | 10 min | Adding a tool means editing and redeploying the agent | A tool added at the gateway, picked up with no redeploy |
| 7 | Running it for real: verification and field positioning | 17 min | Every layer passing alone, none checked together | Every earlier failure case re-run against the whole |
| — | **Total content** | **105 min** | | |
| — | Reserve for room settle, mass login, transitions and overrun | 15 min | | |
| — | **Total slot** | **2 hours** | | |

The schedule budgets 105 minutes into a 120-minute slot deliberately. Every conference session loses time at the front to logistics, and this lab's single mass-login event sits in module 1.

Module 2 carries the most time because none of the three candidate labs in this slot can teach it, and because its diagnosis is the hardest in the lab: the model emitted a correct tool call, the parser did not match it, and the call was left in the response body as text with nothing raising an error.

## Boundaries Against Existing Content

Checked against the published repositories on 2026-09-02 rather than against catalog metadata alone.

| Asset | Overlaps | How this design stays clear |
|---|---|---|
| **vLLM Playground** (`showroom-vllm-playground`) | Its module 3 teaches tool-call parser selection, including the Qwen-to-Hermes pairing. Its module 4 covers MCP integration. | Playground teaches the choice on the happy path: a UI checkbox, a parser dropdown defaulting to Auto-detect, and a reference table by model family, all decided before anything runs. Module 2 here owns the case where that choice is already wrong, nothing reported it, and the evidence is only in the payload. The parser reference table is deliberately not reproduced. |
| **AgentOps in Production** (`agentops-in-prod-showroom`, duplicated in `rhai-features-workshop`) | Observability pillars, metrics, MLflow tracing, evaluations, dev-to-production. Scored 99 percent against the rejected design. | Every one of those modules is gone. MLflow appears here only as the instrument for reading a trace, with no observability objective. |
| **AgentOps in Action** (`agentops-in-action-workshop`) | Identity-aware authorization, runtime isolation, adversarial testing, policy tuning. | The neighbouring slot. Guardrails, adversarial scanning and policy enforcement removed entirely. Module 6 stops at connecting tools through a governed endpoint and carries no assessed outcome. |
| **Agentic AI with Llama Stack** (`showroom-agentic-ai-llamastack`) | RAG, MCP, evaluations, shields, agent frameworks across 14 modules. | Built on Llama Stack, which is being de-emphasized. Module 5 here adds retrieval as one build step and does not tune it. |
| **Red Hat AI Inference** (`redhat-ai-inference`) | Model deployment, benchmarking, Model-as-a-Service, observability. Belongs to the Inference: serving through scale slot. | Confirms why this design is framed as building an agent rather than as an inference lab. That lab owns serving lifecycle, scale and cost. This one touches serving configuration only where it decides whether an agent can call a tool. |
| **Enterprise RAG on Intel** (`enterprise-rag-intel-continuum`) | Full RAG pipeline. | Intel-hardware specific, and module 5 here is a single grounded-answer build step rather than a pipeline. |

**Reusable asset, not a competitor.** `rhpds/vllm-tool-calling` is a deployment quickstart rather than a lab: kustomize manifests providing `servingruntime.yaml` and `chat-template-configmap.yaml` per model per accelerator, with no Showroom content or spec. It is a candidate starting point for provisioning this lab's two endpoints.

**Resolved 2026-09-02.** Module 7 originally carried both end-to-end verification and the customer-conversation work in 13 minutes, which was too tight for a segment whose output is the artifact a Technical Seller takes back to a customer. Two minutes came from module 4 and two from module 6, taking module 7 to 17. Module 2 was deliberately left at 22: it is both the differentiator against every other lab in this slot and the hardest diagnosis in the lab. Module 6 absorbed a cut because it is the narrowest module, carrying one objective and no assessed outcome. Total content is unchanged at 105 minutes and the 15-minute reserve is untouched.

## Difficulty Level

Intermediate

## Environment

**Learner view:** Each participant starts with a pre-provisioned OpenShift AI workbench holding a partially built agent: tool definitions, a stub loop, and a supplied test input. Nothing in it works end to end at the start, and that is the point. Two shared class-wide endpoints serve the same model, one with a deliberately mismatched tool-call parser and one with the validated recipe, and the participant's agent starts pointed at the broken one. Also pre-deployed: an MCP server exposing the lab's tools, an MLflow tracking server reachable by Route, and a populated vector store for module 5.

**Automation needed:** Yes

Automation must provision the workbench per participant with the agent repo pre-cloned; both shared endpoints; the MCP server and its tool definitions; MCP Gateway with per-identity token claims; the MLflow tracking server and Route; the vector store with its corpus already ingested; and a reset path that returns any module to its starting state.

**Provisioning findings from dev-cluster verification (RHOAI 3.4.3):**

- **MCP Gateway is the heaviest item by a wide margin.** Dev-cluster verification went as far as an identity-filtered catalog, which the lab no longer teaches; reaching a working gateway at all took nine non-obvious manual steps, none discoverable from CRD field documentation: gateway namespace admission rules, a hand-created Kuadrant CR, ReferenceGrants for cross-namespace references, an explicit `publicHost`, a real Redis session store on a NetworkPolicy-permitted port, an additive NetworkPolicy for the broker's gRPC ext_proc port, a `ping` method on upstream servers, an `id` field on tools, and a required `spec.prefix`. All of it must be pre-baked. This is a large part of why module 6 is short and supporting rather than a full round.
- **MLflow is a cluster-wide singleton.** The CR must be named `mlflow` and always lands in `redhat-ods-applications` regardless of where it is created, so no per-participant tracking server is possible. This forces the shared-cluster topology.
- **The identity-filtering question is moot rather than deferred.** An earlier version of module 6 taught identity-filtered tool catalogs, which forced a choice between the documented OAuth2 and Authorino path and the ServiceAccount forwarding used in dev-cluster verification. Module 6 no longer teaches filtering, so neither path is built and the per-identity token claims and `userSpecificList` configuration drop out of provisioning.

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
- **Vector store:** PostgreSQL with the pgvector extension, deployed as a plain Deployment via GitOps, holding a read-only corpus ingested at provisioning time. Settled 2026-09-02.

  Chosen because Red Hat OpenShift AI is standardizing on pgvector as a remote vector store provider, so a participant meets the direction the platform is going rather than an arbitrary pick. No operator is required. There is no Milvus, Qdrant, Weaviate or Chroma operator in any catalog on the dev cluster, and the Milvus path runs through OGX, the renamed Llama Stack, which is being de-emphasized and is mid-rename.

  The RHOAI built-in pgvector provider integration is EA2 as of 3.5 and is deliberately **not** used. Module 5's retrieval tool queries Postgres directly, which requires nothing pre-GA, keeps the non-GA dependency count at one, and remains forward-compatible with that integration when it reaches GA.
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
| 6 | A tool registered at the gateway is discovered and used by the agent with no code change, rebuild or restart. |
| 7 | Every earlier failure case re-run against the assembled agent produces the corrected behaviour. No machine-verifiable signal for the positioning segment, which produces a takeaway artifact. |
