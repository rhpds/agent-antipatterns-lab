# Module 5 with the F-21 question, 2026-10-14

Data for decision 0003 (F6, F9). These are the module 5 runs after `m5` changed to "A K-400 is showing fault F-21. What should the technician do?", because the seal service-interval question made the served model refuse. This is data for authoring, not lab prose.

## Environment

- Same as `../2026-10-13-gpu/`: OpenShift AI 3.5.1, one L4, `RedHatAI/Qwen3-8B-FP8-dynamic`, temperature 0, seed 0, non-streaming.
- Endpoint B (`hermes`). The agent and solutions come from `dev` at the time.
- The `user1` pgvector with the 12-passage corpus.
- The agent reached the endpoint through a port-forward. URLs here are rewritten to the in-cluster Service address.

## Runs

| Run | Code | Model calls | Tool calls | Result |
|---|---|---|---|---|
| `m5-start` | `solutions/module-04` (no retrieval) | 2 | `find_part(F-21, K-400)` → `no_results` | Invented: blames "the **temperature sensor** or **control board**", names part `KI-400-CTRL`, which doesn't exist |
| `m5-fixed` | `solutions/module-05` | 2 | `search_bulletins(F-21, K-400)` → `ok`: SB-2024-117 "Applies to" (0.392), SB-2024-102 "Symptom" (0.385) | Grounded cause ("coolant loop pressure low"); its steps aren't the bulletin's "Action", which wasn't retrieved |

Files per run are as in `../2026-10-13-gpu/README.md`: `answer.txt`, `digest.txt`, the raw `NN-request.json` and `NN-response.json`, and `summary.json`.

## Question selection

Each candidate was run without retrieval (`solutions/module-04`) and with it (`solutions/module-05`) on endpoint B:

| Question | Without retrieval | With retrieval |
|---|---|---|
| "What's the recommended service interval for the K-400 coolant pump seal?" | refuses | grounded, SB-2024-117 |
| "How often should the coolant pump mechanical seal on a K-400 be replaced?" | refuses (no universal schedule) | grounded, SB-2024-117 |
| "I'm replacing the coolant pump seal kit on a K-400 today. How many operating hours until it needs replacing again?" | refuses | grounded, SB-2024-117 |
| "What torque should I use on the mounting bolts when replacing the K-600 condenser fan motor?" | refuses | says it's not in the bulletins (SB-2023-088 not retrieved) |
| "What glycol concentration should a K-400 coolant loop run at?" | refuses | says it's not in the bulletins (SB-2024-131 not retrieved) |
| **"A K-400 is showing fault F-21. What should the technician do?"** | **invents** | **grounded cause, SB-2024-102** |
| "A K-900 is showing fault F-21. What should the technician do?" (as a miss case) | invents | reports the gap but adds invented "common triggers", so `m5-miss` stays "What's the service interval on a Kestrel K-900?" |

Every run behind this table is in `candidate-runs.jsonl`: one line per run (20 runs), giving its code, question, tool calls with their arguments and results, and the final answer. URLs are rewritten as above. The raw request and response files were not kept for these runs.

Repeatability of the F-21 question, temperature 0, seed 0:

- **Without retrieval:** 4 runs (the selection run and 3 repeats), all identical, and identical to `m5-start`.
- **With retrieval:** 4 runs, all with the same tool call and the same two passages. The 3 repeats are identical to each other and to `m5-fixed`. The selection run, `20261014-101156-146900`, worded the answer differently: it names SB-2024-102 and replaces the part-number step with "Refer to the full bulletin". So the grounded cause repeats exactly, but the wording held in 3 of 4 runs, not every run.
