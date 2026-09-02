# Module 2. The model interface: making tool calls fire at all

### Brief Overview

The agent declared its tools and never called one. The instinct in the room will be to improve the prompt. The payloads show why that cannot work: the model did emit a tool call, correctly formatted for the model it is, and the parser configured on the endpoint did not match that format, so the call was left in the response body as text and nothing acted on it. No error was raised anywhere, because from vLLM's perspective nothing went wrong.

Participants compare the two class endpoints, find the single differing serving argument, repoint the agent, and watch `tool_calls` populate. None of the three candidate labs in this slot can teach this, because all of them consume a hosted or centrally served model whose serving configuration is not theirs to see.

**Boundary against existing catalog content.** The published *vLLM Playground* lab teaches parser selection in its own module 3, including the Qwen-to-Hermes pairing this module uses. It does so on the happy path: a web UI checkbox, a parser dropdown with an Auto-detect default, and a reference table of parsers by model family, all chosen before anything runs. This module must not restate that. It owns the opposite case, where the choice was already made wrong, nothing reported it, and the only evidence is in the payload. **Do not include a parser-to-model-family reference table.** That is Playground's content and reproducing it converts a complementary module into a duplicate one.

### Audience and Time

Technical Sellers and Services, intermediate. 22 minutes, the largest block in the lab.

Requires module 1, specifically the habit of reading the payload rather than the answer.

### Learning Objectives

- Troubleshoot an agent that never calls a tool by comparing the endpoint's serving arguments against the tool-call format the model was trained to produce.
- Deploy, or in this module repoint to, a vLLM serving runtime configured so that tool calls are emitted and parsed rather than stranded as text.
- Analyze a response payload to distinguish "the model refused to call a tool" from "the model called a tool and nothing parsed it".

### Lab Structure

| Section | Title | Duration |
|---------|-------|----------|
| 1 | Rule out the prompt | 4 min |
| 2 | Find the tool call that was already there | 5 min |
| 3 | Compare the two endpoints | 6 min |
| 4 | Repoint and confirm | 5 min |
| 5 | Why this is a platform property | 2 min |

### Detailed Steps

1. Start from the failed run in module 1. Re-read the response payload: `tool_calls` empty, `content` full.
2. Strengthen the prompt using the supplied stronger instruction, which tells the model explicitly to use the available tool. Re-run.
3. Observe that the answer changes wording and `tool_calls` is still empty. Prompt strength is not the variable.
4. Look at the `content` field closely rather than at the rendered answer. The model's tool call is in there, as text, in the format this model family emits.
5. Draw the conclusion: the model did its job. Something downstream failed to recognise the output.
6. Inspect the serving arguments on both class endpoints. Both set `--enable-auto-tool-choice`. Both set `--reasoning-parser=qwen3`, `--dtype=auto`, `--max-model-len=32768` and `--gpu-memory-utilization=0.90` identically.
7. Identify the single difference: `--tool-call-parser`. One endpoint sets a parser that does not match this model; the other sets `hermes`.
8. Note that the mismatch fails silently rather than loudly. vLLM parsed nothing, found nothing to put in `tool_calls`, and returned a valid response.
9. Repoint the agent's configuration at the validated endpoint. Write the change to the config file on the workbench, not to a shell variable.
10. Re-run the original question from module 1.
11. Confirm in the response payload that `tool_calls` is now populated and `content` no longer holds the call. **This is the module's success signal.**
12. Confirm in the trace that a tool was invoked and its result returned to the model.
13. Note what has not been fixed: the agent now calls tools, and the next module shows it calling the same one indefinitely.

### Key Takeaways

- The parser is model-specific, and the correct pairing is not guessable from the model's name.
- Auto-detection exists and mostly works, which is exactly why the failure is rare enough to be unfamiliar and confusing when it happens. A room that has only ever used auto-detect has never seen this.
- A mismatched parser fails silently. There is no error, no warning, and no degraded status anywhere in the platform.
- Prompt engineering cannot repair a tool call that nothing parsed. The failure is below the prompt.
- Whether an agent can use tools at all is a property of how the model is served, decided before any agent code runs.
- This is invisible on a hosted chat API, which is why it surprises teams who prototype against one and then self-host.

### Infrastructure Notes

- **Two shared class endpoints of the same model**, both pre-provisioned, both setting `--enable-auto-tool-choice`. The validated endpoint sets `--tool-call-parser=hermes`; the broken one sets a deliberately mismatched parser. Model is `RedHatAI/Qwen3-8B-FP8-dynamic`.
- **Do not build the broken endpoint by omitting the flags.** vLLM defaults `tool_choice` to `auto` whenever tools are supplied and then returns HTTP 400 stating that auto tool choice requires `--enable-auto-tool-choice` and `--tool-call-parser`. A loud 400 destroys the module's premise and module 1's demo run, both of which depend on a confident wrong answer.
- **`--reasoning-parser=qwen3` must be set identically on both endpoints and must never be the difference between them.** Red Hat documents a known issue where Qwen3 models emit raw tags when the correct reasoning parser is unavailable. That is a second silent tool-calling failure with a similar symptom and a different cause. If it varies between endpoints, a participant can diagnose the wrong fault and still appear correct.
- **Keep `--max-model-len` at the documented 32768** rather than maximal. Single-GPU throughput degrades under concurrency at very long context lengths, and this module ends with the entire room repointed onto the validated endpoints.
- **The agent must be non-streaming.** Upstream vLLM issue #31871 reports the hermes parser returning raw text instead of parsed `tool_calls` in streaming mode, which is exactly the symptom this module teaches, occurring as a live bug even when configuration is correct. A streaming agent would make the documented fix appear not to work. Verify this early in authoring.
- **The repoint must persist.** Write it to a config file on the workbench PVC, not a session environment variable. A kernel restart over the remaining 80 minutes would otherwise silently return participants to the broken endpoint, and modules 3 to 7 would show this module's symptom with no diagnostic offered for it.
- **Maturity, resolved 2026-08-19.** vLLM serving is GA. The Developer Preview notice on tool calling attaches to standalone Red Hat AI Inference Server, not to the RHOAI/KServe path this lab uses, where these are documented serving-runtime arguments with no preview caveat. That is the absence of a preview label rather than an affirmative support statement; confirming it with the RHOAI product team is an open item for the infra reviewer.
- **Delivery model is self-paced.** The "rule out the prompt" beat in section 1 works best spoken, so the facilitator guide carries the discussion version and the content carries a participant-readable equivalent.
