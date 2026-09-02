# Module 7. Running it for real: verification and field positioning

### Brief Overview

Every layer has been fixed in isolation, and each was verified against the one failure it was built to prevent. Nothing has yet been checked against all of them at once, which is the state most agent projects are in when they ship.

Participants re-run the full set of earlier failure cases against the assembled agent, confirm each corrected behaviour still holds, and record the result as a baseline. The module then converts the build into something a Technical Seller can use in a customer conversation: a short checklist mapping what a customer describes to the layer that causes it.

### Audience and Time

Technical Sellers and Services, intermediate. 13 minutes.

Requires all earlier modules. This is the only module that depends on every one of them.

### Learning Objectives

- Verify the assembled agent end to end against the failure cases from every earlier step before treating it as more than a prototype.
- Demonstrate the relationship between an observed agent symptom and the layer that produces it.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Re-run every earlier failure | 6 min |
| 2 | Record the baseline | 2 min |
| 3 | Symptom to layer | 5 min |

### Detailed Steps

1. Run the supplied regression set. It contains one input per earlier module: the module 1 question that needed a tool, the module 3 multi-step question, the module 4 question that falls outside the backing data, and the module 5 questions inside and outside the corpus.
2. For each, confirm the corrected behaviour in the trace rather than in the answer. Tool calls populate, the run terminates on the model's stop condition, failures surface with a category, retrieval grounds the answer, and the out-of-corpus question returns an explicit gap.
3. Note any case that regressed. The most likely is module 2's repoint reverting after a workbench restart, which is why it was written to a config file rather than an environment variable.
4. Record the run as a named baseline in MLflow, so the assembled behaviour has a reference point that a later change can be compared against.
5. Note what this baseline is and is not: evidence that today's build handles the failures it was built for, and no evidence at all about failures nobody has thought of yet.
6. Work through the symptom-to-layer mapping. A customer says the agent ignores its tools: the serving configuration is where to look first, not the prompt. A customer says it loops or is expensive: the loop is not reading the stop condition. A customer says it confidently reports work it did not do: tool returns are collapsing failure into success. A customer says it makes things up about their own data: nothing is grounding it. A customer asks who can see what: tool access is not going through a governed path.
7. Note the two failure modes this lab covered by discussion rather than hands-on, so participants do not leave believing the list is complete: model and prompt regressions when a model version changes underneath a working agent, and cost behaviour under real concurrency.
8. Take the checklist away as the module's artifact.

### Key Takeaways

- Layers verified in isolation say nothing about the assembly. The regression set is the first evidence that the agent works as one thing.
- A baseline is only meaningful against a later comparison. Recording one is the cheapest thing a team can do before their first change.
- Most reported agent symptoms map to a layer, and the layer is usually below the prompt.
- The five layers in this lab are the ones that break first. They are not the only ones that break.

### Infrastructure Notes

- **The regression set must be supplied and runnable as one command.** Six minutes does not allow assembling inputs by hand, and a participant who is behind must still be able to run it.
- **Every case must have been seen before in its own module.** Nothing new is introduced here. The value is the contrast between the module's original failure and the current behaviour.
- **A participant who is behind must not be blocked.** The regression set should run against whatever state the agent is in and report per-case results, so someone who did not finish module 5 still gets a meaningful result for modules 1 to 4.
- **MLflow is the baseline store**, which is GA and already provisioned for module 1. No new component is introduced in this module.
- **Known tension, flagged for content review.** Thirteen minutes covering both verification and positioning is tight, and the positioning segment is the artifact a Technical Seller carries back to a customer. If review agrees it is too thin, the cleanest correction is moving four minutes from module 2, which is the largest block, rather than reducing the 15-minute reserve. The reserve exists because this lab's mass-login event sits in module 1 and conference sessions lose time at the front.
- **Delivery model is self-paced.** The symptom-to-layer section is the most discussion-shaped part of the lab and benefits most from a facilitator, so it needs a complete participant-readable equivalent in the content, with the discussion prompts in the facilitator guide.
