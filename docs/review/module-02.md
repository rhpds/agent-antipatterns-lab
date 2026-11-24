# Module 2: The model interface review

Notebook checks: **PASS for both participants**, 11 original code cells each. Human content review remains open. Executed source: `94e6ea5563c77853b8b6ae83db66ee5b032f6eee`.

[Notebook source](https://github.com/rhpds/agent-antipatterns-lab/blob/94e6ea5563c77853b8b6ae83db66ee5b032f6eee/notebooks/module-02-model-interface.ipynb) · [Matching Showroom source](../../content/modules/ROOT/pages/module-02-model-interface.adoc) · [Coverage and evidence index](README.md)

## Review checkpoints

- [ ] Reset to module 2 and run the initial question. Expect no executed tools and a stranded `<tool_call>` in response `content`.
- [ ] Send the stronger prompt. Inspect the saved request or prompt column to confirm it changed. Expect no executed tools; the output text may be identical.
- [ ] Compare the same request on endpoints A and B. In ServingRuntime arguments, identify the differing tool-call parser.
- [ ] Save the endpoint B address in `config.toml`, then rerun. Require a real `find_part` result containing `KI-CP-40817`.
- [ ] Recognize repeated lookups or `max_turns` after repointing as the starting loop defect for module 3, not a failed parser fix.

## Evidence and unresolved issues

The author approved replacing the wording-change clause with verification of the stronger saved request. The amendment is committed in `4e1442e`; the scenario title is unchanged. The deterministic and live checks now inspect that request directly. Identical response text is acceptable; executable tool calls before repointing are not.

The evidence index distinguishes the older recorded execution from the accepted candidate run. Fresh catalog provisioning, the separate restart repair and main-branch protection do not follow from this module’s result.

## Recorded execution

[Structured evidence and notebook hashes](evidence/candidate-notebooks.json). The portable package contains both executed notebooks.

- Participant 1: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-9294becb2e74e2e5957522a97e5f73ef) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-dde5e905e58bd38e6af09cb100609f40)
- Participant 2: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-1be92f1bdc6681d476f570bec6dab476) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-6ea928923c8668b65313368ca95730e6)
