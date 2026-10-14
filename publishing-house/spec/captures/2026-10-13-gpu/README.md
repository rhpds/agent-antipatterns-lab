# GPU captures, 2026-10-13

Real model output for modules 1 to 5, captured from the starter agent and its module solutions. This is data for authoring, not lab prose.

## Environment

- OCP 4.22.17 and OpenShift AI 3.5.1, installed from `automation/gitops/bootstrap-infra` with `values-dev-single-l4.yaml`.
- One NVIDIA L4 (AWS g6.2xlarge).
- vLLM image `registry.redhat.io/rhaii/vllm-cuda-rhel9@sha256:c056e61672b6aea489ad5dde0bd2f8497230f5333e87f7cf6c494eba3bfdc808`.
- Model `RedHatAI/Qwen3-8B-FP8-dynamic`, temperature 0, seed 0, non-streaming.
- vLLM flags: `--enable-auto-tool-choice` and `--reasoning-parser=qwen3`.
- Endpoint A: `--tool-call-parser=pythonic`, the mismatched one (see F1).
- Endpoint B: `--tool-call-parser=hermes`, the validated one.
- Only one endpoint ran at a time on the single L4.
- The agent reached each endpoint through a port-forward. Endpoint URLs in these files are rewritten to the in-cluster Service addresses the workbench uses.
- Module 5 used the `bootstrap-tenant` pgvector for `user1`, loaded with `python ingest_corpus.py` (12 passages from 5 bulletins).

## Files

Each directory is one run:

| File | Contents |
|---|---|
| `answer.txt` | What `agent.py` printed |
| `digest.txt` | What `python payloads.py` printed, with the `Run:` and `Full JSON files are in` path lines removed |
| `NN-request.json` / `NN-response.json` | The raw payloads of each model call |
| `summary.json` | Turns, how the run ended, and the tool calls |
| `pod-log-excerpt.txt` | `m1-endpointA-llama3_json` only: the vLLM startup arguments and the first failed request's traceback |

`m1-endpointA-llama3_json` differs from the other runs:
- It has no `summary.json`, because the agent exited on the HTTP 500 before writing it.
- Its `digest.txt` shows the 500 body as "not a completion".
- Its `answer.txt` has the virtualenv path shortened and an `exit=1` line added.
- Its request and response files were saved by curl. The agent's own run saved the same request byte for byte, and the same response JSON.

| Run | Module | Code | Endpoint | Question |
|---|---|---|---|---|
| `m1-endpointA` | 1 | starter | A | `--q m1` |
| `m1-endpointA-strong` | 1 | starter, `--strong-prompt` | A | `--q m1` |
| `m1-endpointA-llama3_json` | 1 | starter; the `m1-endpointA` request replayed with curl | A with `--tool-call-parser=llama3_json` | `--q m1` |
| `m1-endpointB` | 2 | starter | B | `--q m1` |
| `m3-starter` | 3 | starter | B | `--q m3` |
| `m3-fixed` | 3 | `solutions/module-03` | B | `--q m3` |
| `m4-start` | 4 | `solutions/module-03/agent.py`, starter `tools.py` | B | `--q m4` |
| `m4-fixed` | 4 | `solutions/module-04` | B | `--q m4` |
| `m4-fixed-k600-denver` | 4 | `solutions/module-04` | B | "Is the K-600 high-pressure sensor available at the Denver depot?" |
| `m4-fixed-m3` | 4 | `solutions/module-04` | B | `--q m3` |
| `m5-start` | 5 | `solutions/module-04` | B | `--q m5` |
| `m5-fixed` | 5 | `solutions/module-05` | B | `--q m5` |
| `m5-miss-fixed` | 5 | `solutions/module-05` | B | `--q m5-miss` |

## Results

| Run | Model calls | Ended by | Tool calls (arguments) | Tool result categories |
|---|---|---|---|---|
| `m1-endpointA` | 1 | `stop`, `tool_calls` null | none parsed. `content` holds `<tool_call>{"name": "find_part", "arguments": {"query": "coolant pump", "product": "K-400"}}</tool_call>` | none |
| `m1-endpointA-strong` | 1 | `stop`, `tool_calls` null | same stranded call, identical `content` | none |
| `m1-endpointA-llama3_json` | 1 | HTTP 500; the agent exits with `openai.InternalServerError` | none | none |
| `m1-endpointB` | 6 (cap) | turn cap | `find_part(coolant pump, K-400)` ×6, identical | not appended |
| `m3-starter` | 6 (cap) | turn cap, "Stopped after 6 turns without a final answer." | `find_part(coolant pump, K-400)` ×6, identical | not appended |
| `m3-fixed` | 3 | `stop` | `find_part(coolant pump, K-400)`, then `check_stock(KI-CP-40817, Denver)` and `check_stock(KI-SK-40233, Denver)` in one turn | unwrapped starter results |
| `m4-start` | 3 | `stop` | `find_part(high-pressure sensor, K-600)`, `check_stock(KI-HS-60233, Portland)` | `{"results": []}` for Portland |
| `m4-fixed` | 3 | `stop` | same as `m4-start` | `ok`, then `bad_request`: "unknown depot 'Portland'; Kestrel depots are Denver, Phoenix, Chicago" |
| `m4-fixed-k600-denver` | 3 | `stop` | `find_part`, `check_stock(KI-HS-60233, Denver)` | `ok`, then `no_results`: "KI-HS-60233 has no stock at Denver" |
| `m4-fixed-m3` | 3 | `stop` | as `m3-fixed` | `ok`, `ok`, `ok` |
| `m5-start` | 1 | `stop` | none | none |
| `m5-fixed` | 2 | `stop` | `search_bulletins(service interval for coolant pump seal, K-400)` | `ok`, top passage SB-2024-117 "Service interval" |
| `m5-miss-fixed` | 2 | `stop` | `search_bulletins(service interval, K-900)` | `no_results`: "no bulletin passage matched 'service interval' for product 'K-900'" |

Final answers are in each run's `answer.txt`.

## Findings

- **F1. `llama3_json` cannot be the mismatched parser.**
  - With `--tool-call-parser=llama3_json`, vLLM fails every request with HTTP 500: "Llama3JsonToolParser could not locate the bot token '<|python_tag|>' in the tokenizer." Captured in `m1-endpointA-llama3_json/`: the same request as `m1-endpointA`, the 500 response, and the traceback from `vllm/tool_parsers/llama_tool_parser.py`.
  - Module 1 would show a server error instead of a stranded call.
  - `pythonic` gives the designed failure: HTTP 200, `tool_calls` null, and the call left in `content`.
  - This branch switches endpoint A to `pythonic` in `values.yaml` and `values-dev-single-l4.yaml`.
- **F2. Module 1's stronger prompt changes nothing.** `--strong-prompt` gives byte-identical `content`. That supports the module's point that this is not a prompting problem.
- **F3. Qwen3 thinking is on.**
  - Every response carries a separate `reasoning` field. Module 1's single call used 291 completion tokens.
  - `max_tokens = 1024` was not reached in any run.
  - Payload views that show `content` and `tool_calls` are unaffected. The `reasoning` text is visible in `--raw` output.
- **F4. The module 3 fix makes two `check_stock` calls in one turn.** The model looks up stock for both the pump and the seal kit, because `find_part` returns both. The draft's "`find_part` and `check_stock` were each called once" does not hold for the real model: it is one `find_part` and two parallel `check_stock` calls, in 3 model calls.
- **F5. The module 4 starter answer is less dramatic than designed.**
  - With the swallowed error, the model says the sensor "is not currently available at the Portland depot" and offers to check another depot. That treats Portland as a real depot, so the failure stays hidden.
  - It is not the confident in-stock claim the draft describes.
  - After the fix, the answer names the real depots.
- **F6. Module 5's opening run refuses rather than invents.**
  - With the default system prompt and no retrieval tool, the model says it has no access to service intervals and points to the maintenance manual.
  - The module's "confident invention" premise does not hold at temperature 0 with this prompt. This is an authoring decision: change the question or prompt, or reframe the opening.
- **F7. Module 5's miss case works through the product filter.** The model passed `product="K-900"`, and retrieval returned `no_results` without relying on the score threshold. The answer reports the gap and lists K-200, K-400 and K-600.
- **F8. MLflow tracing is not captured.**
  - The direct MLflow Route answers 401 without a token.
  - With a bearer token it answers "Workspace context is required for this request." Setting `MLFLOW_WORKSPACE` makes the client fail with "the remote server does not support workspaces".
  - Trace screenshots for modules 3 to 5 are still needed. The payload files here hold the same calls and results.
- **F9. Module 5's grounded answer adds one unsupported instruction.**
  - `m5-fixed` says "Replace seal kit KI-SK-40233 with pump assembly KI-CP-40817."
  - Its only source is the "Applies to" passage, which says the bulletin covers K-400 chillers fitted with those two parts. It gives no replacement instruction.
  - The interval figures (6,500 hours or 14 months, 4,500 hours for dusty sites or glycol above 35%) are grounded.
  - This supports module 7's point that grounding makes an answer checkable, not correct.
- **F10. Qwen3's reasoning text varies between identical requests.**
  - At temperature 0 and seed 0, byte-identical requests produced different `reasoning` lengths: `m3-starter` call 01 used 277 completion tokens and calls 02 to 06 used 321; `m1-endpointB` call 01 used 291 and calls 02 to 06 used 272.
  - `content` and `tool_calls` were identical in every case, so the captured blocks hold.
  - Participants viewing `--raw` output will see different reasoning text from each other.
