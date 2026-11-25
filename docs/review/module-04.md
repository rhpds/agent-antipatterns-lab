# Module 4: Tool returns review

Notebook checks: **PASS for both participants**, 7 original code cells each. Human content review remains open. Executed source: `94e6ea5563c77853b8b6ae83db66ee5b032f6eee`.

[Notebook source](https://github.com/rhpds/agent-antipatterns-lab/blob/94e6ea5563c77853b8b6ae83db66ee5b032f6eee/notebooks/module-04-tool-returns.ipynb) · [Matching Showroom source](../../content/modules/ROOT/pages/module-04-tool-returns.adoc) · [Coverage and evidence index](README.md)

## Review checkpoints

- [ ] Reset to module 4 and ask about the Portland sensor. The starting tool reply is an empty results list, and the answer incorrectly presents unavailable stock.
- [ ] Copy both supplied solution files. Inspect the error envelope and the agent guidance for interpreting its categories.
- [ ] Repeat the Portland query. Require `check_stock` to return `bad_request` naming the unknown depot, and an answer that says the check could not be completed.
- [ ] Ask the valid Denver sensor query. Require `no_results`, distinct from malformed input.
- [ ] Ask the Denver pump question. Require a successful stock result and the actual returned part number.
- [ ] Inspect the answer as well as the tool category. “Not available at Portland” alone does not explain a failed check.

## Evidence and unresolved issues

The historical GPU run recorded a correct tool error but an incorrect stock explanation. That old row is not accepted as passing evidence for this criterion. The candidate solution adds category interpretation guidance; the review evidence must show the corrected answer, not just a successful tool invocation.

The evidence index distinguishes the older recorded execution from the accepted candidate run. Fresh catalog provisioning, the separate restart repair and main-branch protection do not follow from this module’s result.

## Recorded execution

[Structured evidence and notebook hashes](evidence/candidate-notebooks.json). The portable package contains both executed notebooks.

- Participant 1: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-37799b909efc276d4735930d86a729eb) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-da306770b91d21573735be00722168b5)
- Participant 2: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-8c6973a6bc20e5a1a55acd298f6a5f3b) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-2f4c1b11ccfe6d4b6b3ff11f0a944ffb)
