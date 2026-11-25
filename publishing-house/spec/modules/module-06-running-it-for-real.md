# Module 6. Running it for real: verification and field positioning

### Brief Overview

Every layer has been fixed in isolation, and each was verified against the one failure it was built to prevent. Nothing has yet been checked against all of them at once, which is the state most agent projects are in when they ship.

Participants run the earlier failure cases once against the assembled agent and read the PASS/FAIL table to confirm each corrected behaviour still holds. The module then converts the build into something a Technical Seller can use in a customer conversation: a short checklist mapping what a customer describes to the layer that causes it. It closes by naming governed tool access on the platform, through MCP Gateway, as the next step. That step is named only, with no hands-on work.

### Audience and Time

Technical Sellers and Services, intermediate. 10 minutes, the lab's short closing module.

Requires all earlier modules. This is the only module that depends on every one of them.

### Learning Objectives

- Verify the assembled agent end to end against the failure cases from every earlier step before treating it as more than a prototype.
- Demonstrate the relationship between an observed agent symptom and the layer that produces it.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Re-run every earlier failure | 3 min |
| 2 | Read the PASS/FAIL table | 2 min |
| 3 | Symptom to layer | 4 min |
| 4 | Where to go next | 1 min |
| Stretch | The run as an MLflow evaluation | Not timed |

### Detailed Steps

1. Run the supplied regression set once. It holds five cases, each an input an earlier module failed on: the K-400 coolant pump part number, the Denver depot availability chain, the Portland depot query that silently returns nothing, and the K-400 fault F-21 question alongside the K-900 question that has no answer.
2. Read the PASS/FAIL table the run prints, one row per case. Each verdict is checked in the trace rather than in the answer. Tool calls populate, the run terminates on the model's stop condition, failures surface with a category, retrieval grounds the answer, and the out-of-corpus question returns an explicit gap.
3. Note any case that regressed. The most likely is module 2's repoint reverting after a workbench restart, which is why it was written to a config file rather than an environment variable.
4. Note what this run is and is not: evidence that today's build handles the failures it was built for, and no evidence at all about failures nobody has thought of yet.
5. Work through the symptom-to-layer mapping. A customer says the agent ignores its tools: the serving configuration is where to look first, not the prompt. A customer says it loops or is expensive: the loop is not reading the stop condition. A customer says it confidently reports work it did not do: tool returns are collapsing failure into success. A customer says it makes things up about their own data: nothing is grounding it.
6. Note the two failure modes this lab covered by discussion rather than hands-on, so participants do not leave believing the list is complete: model and prompt regressions when a model version changes underneath a working agent, and cost behaviour under real concurrency.
7. Take the checklist away as the module's artifact.
8. Read the next step. This agent carries its tools in its own configuration, so adding a tool still means editing and redeploying the agent. On OpenShift, MCP Gateway puts an agent's tools behind one endpoint on the platform, so tools can be added or changed without redeploying the agent, and the same endpoint is where access control is applied. A customer who asks who can see what is asking about that path. This lab names it and stops there.

**Stretch goal: the run as an MLflow evaluation.** Re-run the regression set with a name so MLflow records it as an evaluation run: one row per case with its trace and verdict, linked to the agent version that produced it (decision 0005). Open it in MLflow and follow one case from its verdict to its trace. This is optional, and nothing in the module depends on it.

### Key Takeaways

- Layers verified in isolation say nothing about the assembly. The regression set is the first evidence that the agent works as one thing.
- Most reported agent symptoms map to a layer, and the layer is usually below the prompt.
- The four layers in this lab are the ones that break first. They are not the only ones that break.

### Infrastructure Notes

- **The regression set must be supplied and runnable as one command.** Three minutes does not allow assembling inputs by hand, and a participant who is behind must still be able to run it.
- **Every case must have been seen before in its own module.** Nothing new is introduced here. The value is the contrast between the module's original failure and the current behaviour.
- **A participant who is behind must not be blocked.** The regression set should run against whatever state the agent is in and report per-case results, so someone who did not finish module 5 still gets a meaningful result for modules 1 to 4.
- **The PASS/FAIL table is the module's success signal, and it prints in the workbench terminal.** MLflow, GA and already provisioned for module 1, appears only in the stretch goal. No new component is introduced in this module.
- **No baseline comparison.** Recording a named baseline and comparing a later run against it is out of scope. The stretch goal records one evaluation run and stops there.
- **The next step is named, not built.** Section 4 is one paragraph. MCP Gateway is not deployed for the lab, and nothing in the module calls it.
- **Timing set 2026-11-25.** This module was 17 minutes, with a baseline record and nine minutes of symptom-to-layer work. It is now 10, and was renumbered from module 7 to module 6 when the module on connecting tools through the platform was cut.
- **Delivery model is self-paced.** The symptom-to-layer section is the most discussion-shaped part of the lab and benefits most from a facilitator, so it needs a complete participant-readable equivalent in the content, with the discussion prompts in the facilitator guide.
