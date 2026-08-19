# Module 2 — Round 1: Loop discipline and tool-calling configuration

**Module ID:** module-02
**Duration:** 20 min
**Platform layer:** Serve

**Anti-patterns addressed:**

| Beat | Anti-pattern | Source |
|---|---|---|
| A | **The Prompt-Fixable Fallacy** — assuming a missing tool call is a prompt-quality problem, when serving configuration is the cause | *No external source. This is the lab's own framing and must be labelled as such wherever it appears.* |
| B | **The Ungoverned Loop** — running an agent loop that never inspects the model's stop condition, relying on an iteration cap or a text-parsed "done" signal instead | MAST FM-1.5 *Unaware of termination conditions* (12.4%) and FM-1.3 *Step repetition* (15.7%) |

### Brief Overview

The inherited prototype returns a confident, well-written answer to a realistic customer question without ever calling a tool. Participants open the execution trace and find a single model turn and zero tool invocations. The instinct in the room will be to fix the prompt; the trace shows why that cannot work, because the model emitted a tool call and the parser configured on the endpoint does not match the model, so the call was left in the response content as text and nothing acted on it. Once the endpoint is serving with the validated recipe the agent begins calling tools — and immediately exposes a second, independent defect, because the harness never inspects why the model stopped and simply repeats the same call until it hits an iteration cap.

The module runs as two sequenced beats rather than one symptom with two causes, so that every documented fix produces a visible change. Treat that as a requirement. If both defects are fixed at once, participants apply the serving fix, watch the failure persist, and reasonably conclude the fix does not work.

### Audience and Time

**Personas:** Technical Sellers and Services — solution architects, consultants and delivery engineers. Intermediate.

**Assumed on entry:** Participants completed Module 1, so they can open a trace and read model turns and tool invocations. They know what an agent is and have seen one run. They can read Python but are not asked to write it. No prior vLLM experience is assumed.

**Duration:** 20 minutes.

Note on adjacent catalog content: the *VLLM Playground* demo (74% RCARS relevance) covers tool-calling parsers for several model families, but does so as a presenter-led demo driven through a web UI checkbox. This module diagnoses the absence of that configuration from a trace on a real serving deployment. Neither is a prerequisite for the other.

### Learning Objectives

- Analyze an execution trace to distinguish "the model chose not to call a tool" from "the model's tool call was never parsed".
- Troubleshoot a model endpoint's tool-calling configuration by comparing two endpoints' serving arguments, and explain why a mismatched chat template or tool parser causes an agent to silently never call tools.
- Configure an agent loop to inspect the model's stop condition each turn rather than trusting the first response, parsing text for a completion signal, or using an iteration cap as the primary stop mechanism.
- Demonstrate why serving configuration, not prompt quality, is the reason many customer agents silently fail to call tools.

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Beat A — the agent that never calls a tool | 5 min |
| 2 | Beat A fix — repoint to the validated endpoint | 4 min |
| 3 | Beat B — the agent that never stops | 5 min |
| 4 | Beat B fix — inspect the stop condition | 4 min |
| 5 | What this looks like in a customer environment | 2 min |
| — | **Total** | **20 min** |

### Detailed Steps

**Section 1 — Beat A: the agent that never calls a tool (5 min)**

1. Run the inherited agent against the realistic input from Module 1. Observe a fluent, confident answer that contains fabricated order details.
2. Open the trace. Identify two facts: exactly one model turn, and zero tool invocations.
3. Inspect the raw model output field in the trace. The model *did* attempt a tool call — the `<tool_call>` text sits in the content field, `tool_calls` is empty, and `finish_reason` reports `stop`.
4. State the diagnosis explicitly before moving on: this is not a prompting problem. The model emitted a tool call; the serving configuration did not parse it into a structured call the harness could act on.
5. Optional discussion prompt: ask the room what they would have changed first. Most will say the prompt. This is the round's sellable moment — name **The Prompt-Fixable Fallacy** here.

**Section 2 — Beat A fix (4 min)**

6. Inspect both class endpoints and compare their serving arguments. Both set `--enable-auto-tool-choice`. The broken endpoint sets a parser that does not match the model; the validated endpoint sets `--tool-call-parser hermes`.
7. Repoint the agent's model endpoint environment variable to the validated endpoint. (Participants repoint; they do not redeploy a model. The endpoints are shared, class-wide and pre-provisioned.)
8. Re-run the same input. Observe in the trace that `tool_calls` is now populated and the agent invokes a tool.
9. Compare the two parser names against the model being served. The lesson to surface: the parser is model-specific, a wrong one fails silently rather than loudly, and the correct pairing for this model is not guessable from the model's name.

**Section 3 — Beat B: the agent that never stops (5 min)**

10. The same re-run now exposes the second defect. The agent calls the correct tool, receives a valid result, and then calls the same tool again with the same arguments, repeatedly, until the run ends.
11. Open the trace and count the turns. The same tool and arguments recur; the tool result is unchanged each time.
12. Inspect the harness loop code. It advances on a fixed iteration counter and scans the model's text for a completion phrase. It never reads the stop condition the model returns each turn, and it discards each tool result rather than appending it to the message list — so every turn re-sends an identical request and the model has no way to know the work was already done.
13. State the diagnosis: the loop has no reliable termination signal, so it cannot distinguish "the model wants to call another tool" from "the model is finished". Name **The Ungoverned Loop** here.
14. Cite the prevalence — these are the two most common failure modes in the MAST corpus, at 15.7% and 12.4% of observed failures.

**Section 4 — Beat B fix (4 min)**

15. Apply the supplied loop configuration. The loop now branches on the model's stop condition each turn: tool-use, completion, or token exhaustion.
16. Re-run. Observe a clean multi-turn trace: model turn, tool call, tool result, model turn, completion.
17. Confirm the termination is now driven by the model's own stop condition rather than the iteration cap, by checking that the run ends well below the cap.

**Section 5 — Customer framing (2 min)**

18. Summarize the two anti-patterns and the layer each belongs to: one is a serving-configuration defect, the other is harness code. They present as the same symptom to a user and are fixed in completely different places.
19. Hand off to Round 2, where the agent now calls tools successfully but starts calling the *wrong* ones.

### Key Takeaways

- A confident final answer is not evidence that an agent worked. The trace is the evidence.
- An agent that never calls tools is usually a serving-configuration failure, not a prompt failure. No amount of prompt engineering fixes an unparsed tool call.
- The correct chat template and tool parser are model-specific and non-obvious. `hermes` for a Qwen model is the example participants will remember.
- A loop that terminates on an iteration cap or a text-matched "done" string has no reliable stop condition. Inspect what the model reports each turn.
- The same visible symptom can originate at different platform layers. Work out which layer it came from and the fix follows.

### Infrastructure Notes

- **Two shared class endpoints of the same model** are required, both pre-provisioned. Both set `--enable-auto-tool-choice`. The validated endpoint sets `--tool-call-parser hermes`; the broken endpoint sets a deliberately mismatched parser, which fails silently. **Do not build the broken endpoint by omitting the flags** — vLLM defaults `tool_choice` to `auto` whenever tools are supplied and then returns HTTP 400 with "auto tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set", which destroys the round's premise and Module 1's demo run. Model is `RedHatAI/Qwen3-8B-FP8-dynamic`.
- **`--reasoning-parser=qwen3` must be set on BOTH endpoints, and must never be the difference between them.** Red Hat's documented Qwen reference configuration for the KServe vLLM runtime is `--dtype=auto --max-model-len=32768 --enable-auto-tool-choice --tool-call-parser=hermes --reasoning-parser=qwen3 --gpu-memory-utilization=0.90`, and Red Hat documents a known issue where Qwen3 models emit raw tags when the correct reasoning parser is unavailable. That is a second silent tool-calling failure sitting directly beside the one this beat plants, presenting a similar symptom from a different cause. If it is present on only one endpoint, or absent from both, a participant can diagnose the wrong fault and still appear to be right. The only permitted difference between the two endpoints is the `--tool-call-parser` value.
- **Keep `--max-model-len` bounded at the documented 32768 rather than maximal.** Reported vLLM behaviour includes severe single-GPU throughput collapse under concurrency when the context length is set very high, and this round ends with the entire room repointed at the validated endpoints.
- **The agent's endpoint setting must persist**, written to a config file on the workbench PVC rather than a session environment variable. A kernel restart or pod eviction over the remaining 100 minutes would otherwise revert participants to the broken endpoint, and Rounds 2 to 4 would show the Round 1 symptom with no diagnostic for it.
- **Beat A's failure must be forced by the input.** The realistic input has to be unanswerable without a tool — a fact the model cannot hold, in a domain the tool obviously owns — so that a tool call is attempted every time. Whether the model attempts a call is otherwise its own choice, and if it simply answers there is nothing in the trace to point at.
- **Beat B's repetition must come from the harness, not the model.** The loop discards tool results and re-sends an identical message list, so the repeat is caused by code. Do not rely on the model agreeing to repeat itself.
- **The agent must be non-streaming.** Upstream vLLM issue #31871 reports the `hermes` tool-call parser returning raw text instead of parsed `tool_calls` in streaming mode. That is the exact symptom Beat A teaches, occurring as a live bug even when configuration is correct — a streaming agent would make the documented fix appear not to work. This must be verified early in authoring.
- **Beat B's failure must be deterministic.** The repeated tool call has to come from the harness loop structure, not from the model choosing to repeat itself. A stochastic version will not reproduce identically across a room.
- Both beats must reset cleanly so every participant starts from an identical broken state.
- Round 1's maturity commitment, **resolved 2026-08-19**: vLLM serving is GA, and the Developer Preview notice on tool calling attaches to standalone Red Hat AI Inference Server, not to the RHOAI/KServe path this lab uses. On KServe these are documented serving-runtime arguments carrying no preview caveat. Note the precise claim — this is the absence of a preview label rather than an affirmative support statement, and confirming it with the RHOAI product team is an open item for the infra reviewer. See the maturity table in `design.md`.

- **Delivery model is self-paced.** Every instruction, warning and mitigation in this module must appear in participant-facing text. Steps written above as spoken direction — "note out loud", "ask participants", "say this out loud", "point out" — are cues for the separate facilitator guide, and each needs a participant-readable equivalent in the content so nothing depends on a facilitator speaking.

### References

- **MAST — "Why Do Multi-Agent LLM Systems Fail?"** (arXiv 2503.13657, NeurIPS 2025). Source for FM-1.5 *Unaware of termination conditions* and FM-1.3 *Step repetition*, with prevalence figures from the paper's own trace analysis.
- **Frank Coyle, "Anthropic's CCA Exam as a Field-Guide for Agentic Engineering"** (AI Engineer, August 2026). Origin of this lab's anti-pattern-first teaching structure, and the source of the stop-condition discipline framing.
- **Red Hat AI Inference Server — tool calling configuration guide.** Developer Preview.
- Related catalog content, not a prerequisite: **VLLM Playground** (`agd-v2.vllm-playground-aws.prod`).
