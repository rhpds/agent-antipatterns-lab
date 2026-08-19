# Module 4 — Round 3: Observability with MLflow Tracing

**Module ID:** module-04
**Duration:** 18 min
**Platform layer:** Observe

**Anti-patterns addressed:**

| Anti-pattern | Description | Source |
|---|---|---|
| **Silent Success** | A tool failure swallowed into an empty-but-valid result, which the agent reports as a successful answer | MAST FM-3.2 *No or incomplete verification* (8.2%) and FM-3.3 *Incorrect verification* (9.1%) |
| **The Unstructured Error** | Returning failure in a shape that carries no category, no retry signal and nothing a caller can branch on — a free-text string, or a success envelope with the failure buried in a field nothing reads | MAST FC3 *Task Verification*, Insight 3 |

### Brief Overview

The agent reports success. It produces a confident summary of a customer's recent orders, and the summary is built on nothing — a tool returned a well-formed, successful-looking envelope with an empty result set, the agent read it as valid data, and it summarized the emptiness. There is no error anywhere in the output, no exception, and no failed status code.

Participants find the swallowed error in the trace, which is the only place it is visible. They then apply a structured error contract so the failure is returned as a categorized, machine-readable object rather than prose, and add a verification step that checks the result satisfies the request rather than merely that the call returned. The trace makes the failure findable; the contract and the objective check are what stop it recurring.

### Audience and Time

**Personas:** Technical Sellers and Services. Intermediate.

**Assumed on entry:** Participants completed Rounds 1 and 2. The agent calls the right tools and terminates properly, and all tool traffic already runs through MCP Gateway. This round does not extend the gateway; it works on the agent's own error handling and verification. Participants have been reading traces since Module 1.

**Duration:** 18 minutes.

### Learning Objectives

- Monitor an agent with MLflow Tracing and locate a tool failure that the agent reported as a success.
- Implement a structured tool-error contract carrying error category, retryable flag and detail.
- Implement a task-objective verification step that catches a tool result which is well-formed but does not satisfy the request.
- Verify that the previously silent failure now surfaces as a categorized error rather than a confident empty answer.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | The answer built on nothing | 3 min |
| 2 | Finding the swallowed error | 5 min |
| 3 | Fix — the structured error contract | 5 min |
| 4 | Fix — verify the objective, not just the step | 3 min |
| 5 | Re-run and verify | 2 min |
| — | **Total** | **18 min** |

### Detailed Steps

**Section 1 — The answer built on nothing (3 min)**

1. Run the agent against a customer request that requires an order-history lookup.
2. The agent returns a fluent summary stating the customer has no recent orders. It is well-formed, internally consistent, and wrong.
3. Confirm the surface signals: no exception, no error in the output, no failed status. Everything a dashboard would check says this run succeeded.

**Section 2 — Finding the swallowed error (5 min)**

4. Open the trace and step through the tool invocations.
5. Locate the order-history tool call and read its result field. It contains `{"orders": [], "status": "ok"}` — a well-formed, successful-looking envelope, with the failure recorded only in a field nothing reads.
6. Read the following model turn. The model treated that envelope as data, found no orders in it, and reported accurately on what it was given. There was no other reasonable reading available to it.
7. State the diagnosis precisely: the model did not hallucinate and the agent did not malfunction. A tool reported failure as a successful-looking payload, and a successful-looking payload is indistinguishable from data.
8. Name **Silent Success** here, with the prevalence figures — verification failures account for FM-3.2 at 8.2% and FM-3.3 at 9.1% in the MAST corpus.
9. Reinforce the lab's central rule: this failure is invisible in the output and unmissable in the trace. Every check that looked at the output passed.

**Section 3 — The structured error contract (5 min)**

10. Inspect the offending tool's error path. It returns a string on failure.
11. Apply the supplied structured error contract: error category, retryable flag, and detail. Failure becomes an object the caller can branch on.
12. Apply the supplied handling in the agent so a returned error is surfaced rather than passed to the model as content.
13. Note the design principle from MAST's Insight 3 — sole reliance on final-stage, low-level checks is inadequate. A check that only inspects the final answer cannot catch this, because the final answer was fine.

**Section 4 — Verify the objective, not just the step (3 min)**

14. Point out the limit of the fix so far. The structured contract catches failures a tool is honest enough to declare. It does nothing about a tool that returns a well-formed success carrying nothing useful — which is exactly what happened at the start of this module.
15. Apply the supplied verification step. Before the model is allowed to summarize, the harness asserts that the result actually satisfies the request: orders were retrieved for the customer who was asked about. Not that the call returned. Not that the payload parsed. That the objective was met.
16. Ground it in the research, because this is the round's transferable idea. MAST's Insight 3 states that "sole reliance on final-stage, low-level checks is inadequate," and its worked example is a generated chess program that compiles cleanly and is unusable because nothing checked it against the actual rules of chess. Compiling is a low-level check. Playing chess is the objective.
17. Note the measured effect: in the paper's own intervention study, adding a high-level objective verification step produced a 15.6% improvement in task success. Verification is not paperwork, it is the difference between a system that works and one that reports that it worked.

**Section 5 — Re-run and verify (2 min)**

18. Re-run the original request. The agent now reports a categorized, retryable tool failure instead of a confident empty summary, and the objective check refuses to let an unsatisfied result reach the summarizer.
19. Show the same run in the trace, where the failure is now typed and the verification result is recorded alongside it.
20. Hand off to Round 4: the agent is now honest about failure, which raises the question of what happens when it is asked to do something it should refuse.

### Key Takeaways

- Agents convert failure into confident emptiness. The dashboard says green, the run says success, and the answer is built on nothing.
- A tool that reports failure as a successful-looking payload hands the model something indistinguishable from data. The model then reports on it accurately, which is the worst possible outcome.
- Structured errors — category, retryable, detail — give the caller something to branch on. Prose gives it nothing.
- A check that only asks "did the step return?" cannot catch a step that returned the wrong thing. Verify against the objective, not the mechanics.
- Low-level checks passing is not evidence the objective was met. Code that compiles can still fail to play chess.
- Observability is what makes this class of failure findable at all. Nothing in the output would ever have revealed it.

### Infrastructure Notes

- **MLflow is a cluster-wide singleton, verified on 3.4.3.** The CR must be named literally `mlflow`, and it always lands in `redhat-ods-applications` regardless of which namespace the CR is created in. No module instruction may assume a per-project or per-participant MLflow instance. This also constrains topology, since a per-student environment cannot give each participant their own tracking server, and it needs carrying into Phase 5.
- The default CR requests 1 CPU core, which will not schedule on a constrained node. `spec.resources` is tunable directly on the CR and was patched to ~150m on the dev cluster. Worth knowing if the delivered cluster is tight.
- **Known issue RHOAIENG-44516 could not be reproduced on 3.4.3** with a plain ServiceAccount bearer token, against either the direct Route or the AI Gateway URL. What *is* required, and is undocumented, is an `X-MLflow-Workspace: <namespace>` header. The bug may be fixed, or may be specific to workbench-minted tokens rather than ServiceAccount tokens generally — that should be retested with an actual Jupyter-workbench-issued token. **Keep the Route in the module instructions regardless**, since the Route path is proven safe either way and costs nothing. The URI must be pre-set in the workbench image and verified as a pass/fail check in Module 1, not discovered at minute 40.
- The agent's `--trace-dump` fallback (see Module 1) covers the case where the trace backend is unreachable for a participant. Without it, a single bad URI strands someone for the whole lab, because every diagnosis step from Module 1 onward depends on traces.
- **Known issue RHOAIENG-45969 is confirmed real on 3.4.3.** Artifact serving is not enabled by default; `serveArtifacts` and `artifactsDestination` must be set explicitly on the CR, and both are first-class CRD fields. Once set, logging and retrieving artifacts works cleanly end to end. This round does not depend on artifact logging, but provisioning should set the fields anyway so a later module or a curious participant does not hit it.
- Tracing is already enabled from Module 1. This round does not switch instrumentation on. Do not author an "enable tracing" step here.
- The planted failure must be structural, and the failure payload must look like **data rather than an error**. A bare `"Operation failed"` string invites the model to say "the lookup appears to have failed", which destroys the Silent Success framing for whoever gets that response. An empty-but-successful envelope leaves "no recent orders" as the only available reading, which makes the failure deterministic and the lesson sharper.
- Participants arriving from Round 2 should have the gateway in place, since the agent's tool traffic routes through it, but no section of this round configures the gateway. Add an entry assertion and a "behind? run `lab reset --round 3`" callout.
- **Section 4 deliberately does not use MCP Gateway error normalization.** That capability does not appear in Red Hat's published gateway material and was not encountered during dev-cluster verification, which mapped the gateway path in detail. Do not reintroduce it. The verification step is agent-side and depends on nothing pre-GA.
- The objective check must be a deterministic assertion — did this result contain orders for the requested customer — not an LLM judgement. An LLM-based check would reintroduce the failure class this round teaches against.
- MLflow is GA as of OpenShift AI 3.4, delivered via the MLflow Operator, so this round carries no pre-GA exposure.

- **Delivery model is self-paced.** Every instruction, warning and mitigation in this module must appear in participant-facing text. Steps written above as spoken direction — "note out loud", "ask participants", "say this out loud", "point out" — are cues for the separate facilitator guide, and each needs a participant-readable equivalent in the content so nothing depends on a facilitator speaking.

### References

- **MAST — "Why Do Multi-Agent LLM Systems Fail?"** (arXiv 2503.13657, NeurIPS 2025). FM-3.2 *No or incomplete verification* (8.2%), FM-3.3 *Incorrect verification* (9.1%), and Insight 3: "Multi-Level Verification is Needed. Current verifier implementations are often insufficient; sole reliance on final-stage, low-level checks is inadequate." The paper's ChatDev example — code that compiles but fails the actual game rules — is the same failure this round plants, and is worth citing directly in the content.
- **Red Hat OpenShift AI — MLflow Tracing documentation.** GA since 3.4.
- Related catalog content, not a prerequisite: **AgentOps in Production — AI Observability on OpenShift** (`published.agentops-ocp.prod`), Module 4 *Tracing & MLflow*. That workshop teaches observability as its subject; this round uses it to catch one specific failure.
