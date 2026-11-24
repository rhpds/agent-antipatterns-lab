# Module 7: Verification and field positioning review

Notebook checks: **PASS for both participants**, 7 original code cells each. Human content review remains open. Executed source: `5e9341173370f6be15f9b50196246e1e474998e4`.

[Notebook source](https://github.com/rhpds/agent-antipatterns-lab/blob/5e9341173370f6be15f9b50196246e1e474998e4/notebooks/module-07-running-it-for-real.ipynb) · [Matching Showroom source](../../content/modules/ROOT/pages/module-07-running-it-for-real.adoc) · [Coverage and evidence index](README.md)

## Review checkpoints

- [ ] Reset to module 7, reconnect the gateway and confirm the project still has its module 6 delivery registration.
- [ ] Run the named regression baseline. Require six PASS, zero FAIL and zero SKIP for the assembled agent.
- [ ] Open every report row. Require the actual pump, dependent stock lookup, unknown-depot explanation, bulletin citation, explicit search miss and successful one-day delivery result.
- [ ] Confirm each saved run links to its own MLflow trace.
- [ ] Open the named MLflow evaluation. Require six rows, matching assessments and passed/failed/skipped counts of 6/0/0.
- [ ] Run a later named baseline when comparing a change and inspect both evaluations; a report file or command exit alone is insufficient.
- [ ] Use the symptom-to-layer checklist to explain the demonstrated failure layers. Keep concurrency cost and untested model changes outside this result’s scope.

## Evidence and unresolved issues

The historical all-six-PASS result missed an uncited F-21 answer and an ambiguous depot answer. The stronger checks now reject those records. Source citations and failed-check wording use explicit markers rather than an LLM judge; human review must still assess the entire explanation. This is a functionality review, not a load test or release authorization.

The evidence index distinguishes the older recorded execution from the accepted candidate run. Fresh catalog provisioning, the separate restart repair and main-branch protection do not follow from this module’s result.

## Recorded execution

[Structured evidence and notebook hashes](evidence/candidate-notebooks.json). The portable package contains both executed notebooks.

- Participant 1: [Recorded evaluation](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/evaluation-runs?workspace=user-zgrkm-app&selectedRunUuid=1fd48c9f84294f3dbf523652e13d47bd) — 6 PASS, 0 FAIL, 0 SKIP.
- Participant 2: [Recorded evaluation](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/evaluation-runs?workspace=user-zkz8t-app&selectedRunUuid=dfc2a53a703540fb870a572fc2afed37) — 6 PASS, 0 FAIL, 0 SKIP.
