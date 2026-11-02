# Module 1 repeatability, 2026-10-14

`design.md` requires running the module 1 input repeatedly against the broken endpoint before authoring completes. This is that run. It is data for authoring, not lab prose.

## Method

- Same environment as `../2026-10-13-gpu/`: OpenShift AI 3.5.1, one L4, `RedHatAI/Qwen3-8B-FP8-dynamic`, temperature 0, seed 0, non-streaming.
- Endpoint A with `--tool-call-parser=pythonic`, from the chart on `dev`.
- The starter agent from `dev`, `python agent.py --q m1`, default system prompt.
- 10 runs one after another (`seq-01` to `seq-10`), then 10 runs started at the same time (`par-01` to `par-10`). The concurrent runs share vLLM batches, which is the case `design.md` worries about for a full room.
- Every run sent the same request, byte for byte: `request.json`. The 20 per-run copies were compared with it (`cmp`, all identical) and not committed. Each run's response is in `responses/<run>.json`.

## Results

| Runs | `finish_reason` | `tool_calls` | Call stranded in `content` | Distinct `content` | Completion tokens |
|---|---|---|---|---|---|
| `seq-01` to `seq-10` | `stop` ×10 | null ×10 | yes ×10 | 1 | 291 once, 272 ×9 |
| `par-01` to `par-10` | `stop` ×10 | null ×10 | yes ×10 | 1 | 272 ×7, 279 ×3 |

All 20 runs returned the same `content`, which is also identical to `../2026-10-13-gpu/m1-endpointA/`:

```text


<tool_call>
{"name": "find_part", "arguments": {"query": "coolant pump", "product": "K-400"}}
</tool_call>
```

## Findings

- **R1. The module 1 evidence reproduced in 20 of 20 runs.** No run returned a plain refusal or a different call, sequentially or under concurrent load. The recovery line in `design.md` ("if the response body holds a plain refusal ... re-run once") was not needed in this sample.
- **R2. Only the hidden reasoning varied.** Completion tokens ranged over 272, 279 and 291 while `content` and `tool_calls` stayed fixed. This matches finding F10 in `../2026-10-13-gpu/README.md`.
- **R3. Limits of the sample.** 20 runs on one L4 with at most 10 concurrent requests. A room of participants on the event layout (endpoint A on its own GPU) adds more concurrency than this, but on the same single replica.
