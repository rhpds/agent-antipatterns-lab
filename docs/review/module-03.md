# Module 3: The agent loop review

Notebook checks: **PASS for both participants**, 6 original code cells each. Human content review remains open. Executed source: `94e6ea5563c77853b8b6ae83db66ee5b032f6eee`.

[Notebook source](https://github.com/rhpds/agent-antipatterns-lab/blob/94e6ea5563c77853b8b6ae83db66ee5b032f6eee/notebooks/module-03-agent-loop.ipynb) · [Matching Showroom source](../../content/modules/ROOT/pages/module-03-agent-loop.adoc) · [Coverage and evidence index](README.md)

## Review checkpoints

- [ ] Reset to module 3. The endpoint should already be B.
- [ ] Run the Denver pump question before the fix. Require repeated `find_part` calls with the same arguments until the configured cap.
- [ ] Inspect the trace and saved requests. The faulty loop fails to append tool results for the next model call.
- [ ] Copy the module 3 solution and rerun. Require `ended_by: stop`, a lookup result containing `KI-CP-40817` and a subsequent Denver stock check using that returned number.
- [ ] Confirm the pump result is quantity 3, lead time 1 day. A valid seal-kit lookup can add another stock call.
- [ ] In a later request, match each tool response to its assistant call through `tool_call_id`.

## Evidence and unresolved issues

A stop reason or the presence of both tool names alone is insufficient. The stronger verdict rejects a stock request using a placeholder or a number not returned by lookup. Human review still needs to assess whether the explanation makes the two loop defects easy to diagnose.

The evidence index distinguishes the older recorded execution from the accepted candidate run. Fresh catalog provisioning, the separate restart repair and main-branch protection do not follow from this module’s result.

## Recorded execution

[Structured evidence and notebook hashes](evidence/candidate-notebooks.json). The portable package contains both executed notebooks.

- Participant 1: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-67366dfdc62dbe4c2576c176a8d5dd98) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-d92bd549c2901b978eff1f4c1a3a21af)
- Participant 2: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-2cc16c275f26146879132aa855deb0a8) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-73bbe290602b21611d53feb7e5292c91)
