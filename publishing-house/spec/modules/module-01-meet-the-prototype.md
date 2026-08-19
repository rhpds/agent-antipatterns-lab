# Module 1 — Meet the prototype

**Module ID:** module-01
**Duration:** 15 min
**Platform layer:** — (framing and diagnostic method)

**Anti-patterns addressed:** none planted. This module establishes the diagnostic method the four rounds depend on, and the habit the whole lab is built to break — judging an agent by its final answer.

### Brief Overview

Participants inherit an agent prototype that is about to ship. It was built by someone else, it demos perfectly, and the person who wrote it is not in the room. They run it against the input it was demoed with and it works. They run it against a realistic customer input and it produces a confident, fluent, wrong answer.

The module then introduces the one tool every later round depends on: the execution trace. Participants learn to read model turns, tool invocations, tool results and stop conditions, and to treat the trace rather than the output as the evidence of what happened. Nothing is fixed here. The point is to establish that the final answer is not a reliable signal, and that there is somewhere else to look.

### Audience and Time

**Personas:** Technical Sellers and Services — solution architects, consultants and delivery engineers. Intermediate.

**Assumed on entry:** Participants know what an LLM agent is and have built or demoed one. They can log in to the OpenShift console, switch project, and view a pod log. They can read Python. No prior experience with vLLM, MCP, MLflow or TrustyAI.

**Duration:** 15 minutes as budgeted, but treat that figure with suspicion. This module has no planted failure to diagnose, yet it contains the lab's only mass-login event, and section 2 is the tightest three minutes of the day. Pre-starting workbenches is what makes the budget survivable; without it, plan for eight to twelve minutes here and take the difference from Module 6.

### Learning Objectives

- Verify access to the pre-provisioned OpenShift AI environment, the agent prototype, and the shared class model endpoints.
- Demonstrate the gap between an agent that passes its demo input and the same agent on realistic input.
- Analyze an execution trace to identify model turns, tool invocations, tool results and stop conditions.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Framing — the prototype-to-production gap | 3 min |
| 2 | Environment check and the inherited agent | 3 min |
| 3 | Run it green, then run it red | 4 min |
| 4 | Reading the trace | 5 min |
| — | **Total** | **15 min** |

### Detailed Steps

**Section 1 — Framing (3 min)**

1. Set up the premise. The agent works, it is scheduled to ship, and four things are wrong with it that no amount of testing against the demo input will reveal.
2. State the structure of the next two hours: four rounds, each following the same rhythm — the agent fails plausibly, you diagnose from the trace, you apply a supplied configuration to a named platform component.
3. Make the framework-independence point early, because it is what makes the lab worth their time: a tool-description collision misroutes in LangGraph, Google ADK and CrewAI alike. The failures belong to the platform layer, not the framework layer.

**Section 2 — Environment check (3 min)**

4. Log in to the OpenShift AI dashboard and open the pre-provisioned workbench.
5. Confirm the agent prototype repository is present and its dependencies are installed.
6. Confirm connectivity to the shared class model endpoints. There are two, serving the same model; the agent is pointed at one of them and the difference between them is Round 1's subject. Do not explain the difference yet.
6a. Confirm the trace backend is reachable as an explicit pass or fail check, not an assumption. Traces are the evidence for every diagnosis from here on, so a participant whose tracing is broken must be caught now rather than at minute 40.
7. Walk the agent's structure briefly: tool definitions, the loop, the system prompt. Participants read it; they do not modify it yet.

**Section 3 — Run it green, then red (4 min)**

8. Run the agent against the demo input it was built with. It answers correctly. Note out loud that this is the evidence the prototype shipped on.
9. Run the same agent against a realistic customer input. It returns a fluent, confident answer containing fabricated details.
10. Ask participants to identify what is wrong from the output alone. The intended outcome is that they cannot — the answer looks entirely plausible.

**Section 4 — Reading the trace (5 min)**

11. Open the trace for the failed run.
12. Identify each element in turn: model turns, tool invocations, tool results, and the stop condition reported per turn.
13. Point out the specific fact that will matter in the next module: one model turn, zero tool invocations.
14. Do not diagnose it yet. The goal is that participants know where to look and what the parts are called.
15. State the rule the rest of the lab runs on: the final answer is a claim, the trace is the evidence.

### Key Takeaways

- An agent that passes its demo tells you almost nothing about how it behaves on real input.
- Agent failures are usually invisible in the output and obvious in the trace.
- A trace has a small vocabulary — model turns, tool invocations, tool results, stop conditions — and reading it is a learnable skill, not a specialism.
- The failures ahead are structural and framework-independent. They recur regardless of which agent framework produced them.

### Infrastructure Notes

- Requires the pre-provisioned OpenShift AI workbench with the prototype repository already cloned and dependencies installed. Participants should not spend lab time on `pip install`.
- The agent starts pointed at the **broken** model endpoint — the one serving `--enable-auto-tool-choice` with a parser that does not match the model. That is what makes the realistic input fail. Do not fix it here. The broken endpoint must not simply omit the tool-calling flags: vLLM defaults `tool_choice` to `auto` whenever tools are supplied and then rejects the request with HTTP 400, which would break the demo input in this module as well as the diagnosis in Round 1.
- The demo input in section 3 must be answerable without a tool call, so it succeeds against the broken endpoint. The realistic input must be unanswerable without one — a fact the model cannot hold, in a domain a tool obviously owns — so the failure is forced by the input rather than left to the model's discretion.
- Workbenches must be pre-started before participants arrive. This module contains the lab's only mass-login event and a cold workbench pulling its image costs one to three minutes per participant.
- The agent needs a `--trace-dump` mode that prints the same turn, tool and stop-condition structure to stdout. If the trace backend is unreachable for a participant, that fallback keeps every diagnosis step in the lab workable.
- Trace instrumentation is already enabled and traces are already flowing when the module starts. Round 3 deepens what participants do with traces; it does not switch tracing on. Nothing in the lab should ask participants to enable instrumentation they already have.
- The demo input and the realistic input must both be fixed, scripted inputs. The contrast between them is the entire point of section 3 and cannot depend on the model's mood.
- Budget for environment failures here rather than later. This is the module where a broken workbench surfaces.

- **Delivery model is self-paced.** Every instruction, warning and mitigation in this module must appear in participant-facing text. Steps written above as spoken direction — "note out loud", "ask participants", "say this out loud", "point out" — are cues for the separate facilitator guide, and each needs a participant-readable equivalent in the content so nothing depends on a facilitator speaking.

### References

- **Frank Coyle, "Anthropic's CCA Exam as a Field-Guide for Agentic Engineering"** (AI Engineer, August 2026). Origin of the anti-pattern-first teaching structure this lab uses.
- **MAST — "Why Do Multi-Agent LLM Systems Fail?"** (arXiv 2503.13657, NeurIPS 2025). Source of the failure-mode prevalence figures cited in later modules.
- **Microsoft AI Red Team, "Taxonomy of Failure Modes in Agentic AI Systems", version 2.0** (whitepaper dated April 2026; announced June 2026). Source for the security-side failure modes in Rounds 2 and 4.
