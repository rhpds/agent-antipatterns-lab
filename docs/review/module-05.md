# Module 5: Knowledge search review

Notebook checks: **PASS for both participants**, 7 original code cells each. Human content review remains open. Executed source: `5e9341173370f6be15f9b50196246e1e474998e4`.

[Notebook source](https://github.com/rhpds/agent-antipatterns-lab/blob/5e9341173370f6be15f9b50196246e1e474998e4/notebooks/module-05-knowledge-search.ipynb) · [Matching Showroom source](../../content/modules/ROOT/pages/module-05-knowledge-search.adoc) · [Coverage and evidence index](README.md)

## Review checkpoints

- [ ] Reset to module 5 and ask about F-21. Observe the unsupported starting answer and absence of a retrieval call.
- [ ] Query `retrieval.py` directly and inspect the bulletin IDs and passage text.
- [ ] Copy the module 5 solution. Ask F-21 again and require a successful `search_bulletins` result containing `SB-2024-102`.
- [ ] Check that the answer cites `SB-2024-102` and uses its “coolant loop pressure low” cause.
- [ ] Ask about the nonexistent K-900. Require `no_results` from bulletin search and an answer acknowledging the gap rather than an invented interval.
- [ ] Open the RETRIEVER span and compare its document IDs/text with what the tool returned.

## Evidence and unresolved issues

The solution now explicitly requests source IDs and acknowledgement of search misses. A source marker is a bounded deterministic check, not a general proof that every statement is entailed by the bulletin. Human review should inspect the suggested actions as well as the cited symptom.

The evidence index distinguishes the older recorded execution from the accepted candidate run. Fresh catalog provisioning, the separate restart repair and main-branch protection do not follow from this module’s result.

## Recorded execution

[Structured evidence and notebook hashes](evidence/candidate-notebooks.json). The portable package contains both executed notebooks.

- Participant 1: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-100659bc23e6f4c60ad4160914b554e8) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/1/traces?workspace=user-zgrkm-app&selectedEvaluationId=tr-b6d6ad8df4777d35cf895384553eaf9f)
- Participant 2: [Starting trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-f7d1399461c90ce6f66db1f770fac201) · [Corrected-path trace](https://rh-ai.apps.ocp.6hs5h.sandbox1714.opentlc.com/mlflow/#/experiments/2/traces?workspace=user-zkz8t-app&selectedEvaluationId=tr-d1b1b55e8b9171212c10b76d678eded7)
