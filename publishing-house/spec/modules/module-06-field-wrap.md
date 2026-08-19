# Module 6 — Field wrap and positioning

**Module ID:** module-06
**Duration:** 15 min
**Platform layer:** — (synthesis and customer framing)

**Anti-patterns addressed:** none new. This module consolidates all seven named across the four rounds into a customer conversation script, and names two further failure modes the lab covers by discussion rather than hands-on.

**Delivery note.** This module is the most facilitator-dependent in the lab. The participant-facing content must still stand alone — the conversation table and the reading list are the takeaway artifact and must be readable without a person present — but the discussion beats in sections 3 and 4 belong in the facilitator guide.

### Brief Overview

Participants have spent 90 minutes across four rounds fixing an agent they did not write. This module converts that into something they can use in front of a customer on Monday: what the customer will describe, which failure mode it maps to, and which Red Hat AI capability addresses it.

It also names two failure modes the lab deliberately does not do hands-on — self-reported model confidence as a routing signal, and escalation design — so that participants know the map is larger than the four rounds and know where the edges are.

The module closes on why these four rounds are worth remembering, which is that no single published taxonomy contains all of them.

### Audience and Time

**Personas:** Technical Sellers and Services. Intermediate.

**Assumed on entry:** All four rounds complete. Participants have a working agent that calls tools correctly, terminates properly, reports failures honestly, and enforces a compliance rule outside the model.

**Duration:** 15 minutes, discussion-led rather than hands-on. This is the module to compress if earlier rounds overrun, but the conversation script in section 2 should survive any cut.

### Learning Objectives

- Demonstrate the four failure modes and the corresponding Red Hat AI capability in a customer conversation.
- Analyze a customer's description of agent trouble and map it to the platform layer where the fix belongs.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | What was built — the four layers in review | 3 min |
| 2 | The customer conversation script | 6 min |
| 3 | Two failure modes not covered hands-on | 3 min |
| 4 | Why these four, and Q&A | 3 min |
| — | **Total** | **15 min** |

### Detailed Steps

**Section 1 — What was built (3 min)**

1. Review the agent as it now stands against the agent participants inherited, round by round.
2. Reinforce the through-line: each round's symptom appeared in the output as a confident answer, and each round's cause lived at a different platform layer.

**Section 2 — The customer conversation script (6 min)**

3. Work through the mapping as a table participants can take away. For each row: what the customer says, which anti-pattern it is, and which capability addresses it.

   | Layer | What the customer describes | Anti-pattern | Red Hat AI capability |
   |---|---|---|---|
   | Serve | "It just answers, it never actually looks anything up" — or "it goes round in circles until it times out" | **The Prompt-Fixable Fallacy**, and **The Ungoverned Loop** | vLLM tool-calling configuration. The loop half is fixed in the harness, inside the same round — worth saying plainly, because it is the one fix in the lab that is code rather than product. |
   | Govern | "It uses the wrong tool and we only find out from the customer" | **Tool Overload**, and **Description Collision** | MCP Gateway |
   | Observe | "It says it worked and it didn't" | **Silent Success**, and **The Unstructured Error** | MLflow Tracing, plus a structured error contract and an objective check |
   | Enforce | "It follows the compliance rule except when it doesn't" | **Prompt as Policy** | TrustyAI Guardrails Orchestrator, Kuadrant AuthPolicy, verified with Garak via EvalHub |

4. Practise the diagnostic move rather than the memorization: when a customer describes symptoms, the question is which layer the fix belongs to. Serving configuration, harness code, tool governance, observability, or enforcement.
5. Note which of these are conversations the field can start immediately and which need a platform team in the room.

**Section 3 — Not covered hands-on (3 min)**

6. **Self-reported confidence as a routing signal.** Agents asked how sure they are will answer, and the answer carries little information. Routing consequential decisions on it is a common design error. Covered by discussion because the product story is thin, not because the failure is rare — MAST records *fail to ask for clarification* at 6.8% of observed failures.
7. **Escalation design.** What the agent does when it cannot proceed, and who it hands to. Largely an organizational design question rather than a platform one.
8. Point briefly at the scope boundary: sandboxing and isolated execution are real and are covered by the sibling Agents security and governance material, not here.

**Section 4 — Why these four (3 min)**

9. Make the closing argument, which is also the reason the lab exists. No single published taxonomy contains all four failures. Rounds 1 and 3 are reliability failures, catalogued in the academic literature — MAST, built from 1600-plus annotated traces. Rounds 2 and 4 are security failures, catalogued by Microsoft's AI Red Team and OWASP. Practitioners tend to read one literature or the other, so the four failures that most often kill production agents never appear together in one place.
10. Point participants at the References section for follow-up.
11. Q&A.

### Key Takeaways

- The same customer complaint — "it gave a confident wrong answer" — maps to four different causes at four different platform layers.
- Diagnosis is the transferable skill. The specific fixes change with the platform; working out which layer is at fault does not.
- These failures are framework-independent. A description collision misroutes in LangGraph, Google ADK and CrewAI alike, which is why the durable investment is the platform layer.
- Reliability failures and security failures are documented by different communities. Agents in production produce both.

### Infrastructure Notes

Nothing to provision. This module runs on the environment as it stands at the end of Round 4. If the schedule has slipped, sections 3 and 4 compress; section 2 should not.

### References

Consolidated reading list for participants, and the source list for the lab's anti-pattern names.

- **MAST — "Why Do Multi-Agent LLM Systems Fail?"** (arXiv 2503.13657, Berkeley, NeurIPS 2025). Fourteen failure modes from 1600-plus annotated traces. Source for The Ungoverned Loop (FM-1.5, FM-1.3), Silent Success (FM-3.2, FM-3.3), and The Unstructured Error (FC3 *Task Verification*, Insight 3, which also supplies Round 3's objective-verification remediation and its measured +15.6% result).
- **Frank Coyle's "specialize, don't overload"** is the source for Tool Overload; see the Coyle entry below.
- **Microsoft AI Red Team, "Taxonomy of Failure Modes in Agentic AI Systems", version 2.0** (whitepaper dated April 2026; announced June 2026). Source for Description Collision (§4.8, §4.3) and Prompt as Policy (§4.4).
- **OWASP GenAI Security Project — Top 10 for Agentic Applications (2026).** ASI01 *Goal Hijacking*, ASI02 *Tool Misuse*, ASI04 *Supply Chain*.
- **Red Hat, *Why prompt-level guardrails aren't enough: The platform security layers production agents need***.
- **Red Hat Developer, *Architect an open blueprint for cloud-native AI agents*** (July 2026).
- **Frank Coyle, "Anthropic's CCA Exam as a Field-Guide for Agentic Engineering"** (AI Engineer, August 2026). Origin of this lab's anti-pattern-first structure.

**Note on one name.** *The Prompt-Fixable Fallacy* is this lab's own framing and has no external source. It must be presented as such wherever it appears, and never listed alongside the cited patterns without that distinction.
