# Module 6: Platform tool access review

Notebook checks: **PASS for both participants**, 11 original code cells each. Human content review remains open. Executed source: `5e9341173370f6be15f9b50196246e1e474998e4`.

[Notebook source](https://github.com/rhpds/agent-antipatterns-lab/blob/5e9341173370f6be15f9b50196246e1e474998e4/notebooks/module-06-platform-tool-access.ipynb) · [Matching Showroom source](../../content/modules/ROOT/pages/module-06-platform-tool-access.adoc) · [Coverage and evidence index](README.md)

## Review checkpoints

- [ ] Start with a project whose delivery tool is not yet registered. Reset restores agent files but does not unregister project tools.
- [ ] Run the Denver pump question locally and retain its stock facts.
- [ ] Set the provided gateway URL in `config.toml`. Stop if a cell says the URL is missing or “Set gateway_url first”.
- [ ] Repeat the pump question through the gateway. Verify prefixed tool names and a dependent stock check using `KI-CP-40817`, with the same Denver pump stock facts as locally.
- [ ] Inspect the initial gateway catalog and ask the delivery question. `estimate_delivery` must be absent before registration.
- [ ] Register the tool from the notebook in the participant project. Rediscover it if registration caching delays its appearance.
- [ ] Ask again. Require a successful Denver-to-Boulder result with `transit_days: 1` and an answer reporting one day, without another agent edit or restart.
- [ ] Keep participant isolation distinct from discovery: the other participant must not see this registration until registering it independently.

## Evidence and unresolved issues

The historical run used `KI-XX-00000` through the gateway and did not preserve the local pump behavior. The candidate guidance requires actual returned part numbers. The check permits additional valid seal-kit lookups while requiring matching pump stock. This notebook run demonstrates each participant’s behavior; the earlier complete workshop run separately recorded catalog isolation through the same deployed tool server.

The evidence index distinguishes the older recorded execution from the accepted candidate run. Fresh catalog provisioning, the separate restart repair and main-branch protection do not follow from this module’s result.

## Recorded execution

[Structured evidence and notebook hashes](evidence/candidate-notebooks.json). The portable package contains both executed notebooks.

- Participant 1: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-3e7e9ba696b90421b075e40c658dccfb) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-e4bfd4c51ed4229b8b520e6966538d10) · [Delivery trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-a641df15c5db96e3733626c28ec2fa1e)
- Participant 2: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-e5d67b71ff106a8e99079afe90b44816) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-903ea7765a332e469251783c19bdd3ea) · [Delivery trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-4580311844fff734cb37a6d9a08d6f47)
