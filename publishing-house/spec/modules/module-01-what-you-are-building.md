# Module 1. What you are building, and how to see inside it

### Brief Overview

Participants meet the agent they will spend the next hundred minutes building, and establish the one habit the whole lab depends on. They run it once against a realistic question. It answers confidently and the answer is invented, because at this point the agent has tool definitions but nothing that makes tool calls happen. Rather than fixing anything, they learn to look at the request and response payloads on the inference endpoint and at the resulting trace, and to treat the agent's answer as a claim rather than as evidence.

Nothing is built in this module. Its output is a working habit and a baseline everyone can return to.

### Audience and Time

Technical Sellers and Services, intermediate. 12 minutes. This module carries the lab's single mass-login event, which is why the schedule holds 15 minutes of reserve against a 105-minute content budget.

No prerequisites beyond the lab's own: OpenShift console familiarity and the ability to read Python.

### Learning Objectives

- Analyze the request and response payloads on an inference endpoint to determine what the model was asked and what it actually returned.
- Verify that an agent's confident answer is unsupported by locating the absence of any tool invocation in the trace.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Find the pieces | 2 min |
| 2 | Run the agent once | 4 min |
| 3 | Read the payload | 5 min |
| 4 | The rule for the rest of the lab | 1 min |

### Detailed Steps

1. Open the workbench, which is already running from the pre-lab step.
2. Open the agent project. Identify the three files that matter: the tool definitions, the loop, and the configuration that names the model endpoint.
3. Note that the endpoint currently configured is the one the lab starts on. Do not change it yet.
4. Open the supplied test question: *"A customer's K-400 is showing a coolant pressure fault. What's the replacement part number for the coolant pump?"* Kestrel Industrial is fictional, so the model cannot know the answer, and `find_part` obviously owns it.
5. Run the agent. It returns a fluent, specific, confident answer in a few seconds.
6. Note the answer. It is wrong, and nothing about its presentation says so.
7. Open the request payload that the agent sent. Confirm the tools were declared: the `tools` array is populated.
8. Open the response payload. Observe that `tool_calls` is empty and `content` holds the entire answer.
9. Open the MLflow trace for the run. Confirm what the payloads already showed: one model turn, zero tool invocations, and a stop reason that indicates the model simply finished talking.
10. State the rule that the rest of the lab runs on: the answer is a claim, and the evidence is somewhere else. Every module from here ends by checking evidence rather than by reading the answer. Say which evidence: payloads in this module and the next, because their failure is visible nowhere else, and the trace from module 3 onward, which is the better instrument once turn counts, tool sequences and error categories are what matter.
11. Do not diagnose the cause yet. Module 2 opens on exactly this failure.

### Key Takeaways

- An agent that produces no error and no warning can still be doing nothing at all.
- Tool definitions being present in the request proves only that they were offered, not that they were used.
- `tool_calls` and the stop reason answer in one glance what reading the prose never will.
- Fluency is uncorrelated with correctness, and it is the reason agent failures survive review.

### Infrastructure Notes

- **The starting endpoint is the deliberately mismatched one.** The failure in this module is the same one module 2 diagnoses, seen without explanation. Do not reveal the cause here.
- **The test question must be unanswerable without a tool.** Kestrel part numbers exist nowhere outside the lab's fixture data, so the model cannot answer from memory and attempts a `find_part` call every time. Verify during authoring that it invents a plausible part number rather than refusing, since a refusal gives the participant nothing in the payload to point at.
- **MLflow authentication needs the documented workaround.** Known issue RHOAIENG-44516: Kubernetes tokens are not accepted through the OpenShift AI Gateway, so `MLFLOW_TRACKING_URI` must point at a direct Route. Known issue RHOAIENG-45969: artifact serving backed by S3 is not configured by the automatic workbench integration, so parameters, metrics and tags log correctly but `log_artifact()` needs manual setup. This module only needs the former.
- **The payload view must be first-class, not an afterthought.** Participants need a reliable way to see the raw request and response, whether that is a logging wrapper in the supplied agent code or a saved file per run. The trace supplements it. Reading the wire is the lab's differentiator and it cannot depend on a participant knowing how to enable debug logging.
- **Login and workbench startup are a pre-lab step, not part of this module's 12 minutes.** Budgeting four minutes for thirty conference logins plus thirty workbench pods pulling images and binding PVCs was not realistic; workbench spawn alone routinely takes several minutes at that concurrency. Participants must arrive with the console open and the workbench running. The lab guide's front matter carries the login instructions, and the room needs them done before the clock starts. If this is not enforced, module 1 consumes the entire 15-minute reserve and every later module runs at zero margin.
- **This module must survive 30 simultaneous first runs.** Every participant hits the same broken endpoint within the same two minutes, and it is a single vLLM instance on GPU 0 rather than one of the three validated replicas. This is the lab's peak synchronized load and it lands on its least redundant component.
- **Recovery line required in participant text.** With greedy decoding and a fixed seed the model's response to the module 1 input is the same for everyone, but the evidence still depends on the model attempting a tool call. The content must tell participants what to do if their response body holds a plain refusal instead of a stranded tool call: re-run once, and note that module 2's diagnosis is unchanged either way.
- **Delivery model is self-paced.** Steps written above as spoken framing, such as stating the rule in section 4, need a participant-readable equivalent in the content. The facilitator guide carries the discussion version.
