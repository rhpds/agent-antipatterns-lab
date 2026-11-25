# Module 6: Running it for real review

The closing module since the 2026-11-25 scope cut, which removed the MCP Gateway module. It replaces the former module 7 and is about 10 minutes long. Notebook checks: **not yet executed on a live workshop** for this version. Human content review remains open.

[Notebook source](../../notebooks/module-06-running-it-for-real.ipynb) · [Matching Showroom source](../../content/modules/ROOT/pages/module-06-running-it-for-real.adoc) · [Coverage and evidence index](README.md)

## Review checkpoints

- [ ] Reset to module 6 and run the regression cell straight after it, with nothing to connect, register or configure first.
- [ ] Require five PASS, zero FAIL and zero SKIP for the assembled agent, each with its reason.
- [ ] Open every report row. Require the actual pump, dependent stock lookup, unknown-depot explanation, bulletin citation and explicit search miss.
- [ ] Confirm the notebook explains a cut-off case: FAIL, with a reason that says to run the set again.
- [ ] Use the symptom-to-layer checklist to explain the demonstrated failure layers. "Who can see what?" points to governed tool access on the platform as a next step, with no hands-on step. Keep concurrency cost and untested model changes outside this result's scope.
- [ ] Optional (stretch goal): open the named MLflow evaluation run, `closing-run`. Require five rows, matching assessments and passed/failed/skipped counts of 5/0/0. Skipping it leaves the module complete.

## Evidence and unresolved issues

Source citations and failed-check wording use explicit markers rather than an LLM judge; human review must still assess the entire explanation. This is a functionality review, not a load test or release authorization.

## Recorded execution

None yet for this version. The recorded evaluations in [the evidence index](evidence/candidate-notebooks.json) come from the former module 7 at `5e9341173370f6be15f9b50196246e1e474998e4`, with six cases including the removed gateway case. They don't stand for this module.
