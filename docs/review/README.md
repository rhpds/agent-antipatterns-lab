# Modules 2–7 review

Review the modules in order, beginning with [module 2](module-02.md). Each checklist identifies the intended starting failure, the supplied fix, observable success and the remaining human judgment. The notebooks remain the source of the matching Showroom pages.

The review implementation is `5e9341173370f6be15f9b50196246e1e474998e4`. All six modules have passing notebook checks for both participants: **12 accepted executions, 98 original code cells**, and two recorded module 7 evaluations with **6 PASS, 0 FAIL, 0 SKIP** each. Human content review remains open.

[Structured execution evidence](evidence/candidate-notebooks.json) contains per-module source commits, tool results, answers, trace links, evaluation links and notebook hashes. Modules 2–4 retain their passing executions at `94e6ea5`; the only runtime change afterward was the module 5 solution, so affected modules 5–7 were rerun at `5e93411`. [Source equivalence](evidence/source-equivalence.json) records that boundary. The later review commit adds checklists, evidence, source-link attribution and a troubleshooting paragraph, with no further agent or notebook-code change.

| Module | Review checklist | What to look for |
|---|---|---|
| 2 | [Model interface](module-02.md) | Changed saved prompt, stranded versus parsed calls, actual pump returned |
| 3 | [Agent loop](module-03.md) | Repeated starting loop, matched tool messages and dependent stock lookup |
| 4 | [Tool returns](module-04.md) | Failed check versus actual empty stock, in both tool result and answer |
| 5 | [Knowledge search](module-05.md) | Unsupported starting claim, cited bulletin and explicit search miss |
| 6 | [Platform tool access](module-06.md) | Matching pump facts through the gateway, independent delivery registration |
| 7 | [Verification](module-07.md) | Six passing cases, zero skips and matching recorded MLflow evidence |

[Acceptance coverage audit](coverage.md) maps every approved scenario to its assertions and test definitions. The amended stronger-prompt scenario was approved before its test binding changed; identical model wording is acceptable when the stronger request is recorded and tools still do not execute.

## Evidence boundaries

The earlier complete run at `9787626` passed the old live checks but missed a wrong gateway part number and incomplete answer evidence. Its [reassessed records](evidence/historical-reassessment.json) preserve those findings rather than relabeling the original run as sufficient. In that JSON, the changed-wording observation records the former clause; the approved amendment supersedes that clause.

A first repair candidate (`5cee4f6`) fixed the gateway chain and answer markers, but closer review found that its broad module 4 guidance suppressed module 5’s intended starting invention. One module 7 model response also [exhausted its 1,024-token budget](evidence/token-budget-failure.json) before answering. The first repair’s [suppressed starting failure](evidence/first-repair-regression.json) and the later [missing source citation](evidence/citation-failure.json) are retained as failed attempts. Those attempts remain failures. The current candidate applies module 4 interpretation guidance only after an actual error, explicitly checks the unsupported starting claim and allows up to 4,096 output tokens including reasoning. A token cap, timeout or missing case is still a failed result, never a hidden retry.

The accepted notebook runs use isolated candidate checkouts in both existing workbenches, the cluster’s Qwen model, actual model endpoints, pgvector, MLflow and the MCP gateway. They leave participant source checkouts untouched. Module 6’s test registration is returned to the original project data after module 7. This is notebook review evidence in the repaired workshop, not proof of fresh catalog provisioning.

The fixed checks inspect known fixture facts and selected answer markers. They do not establish general semantic accuracy, arbitrary-query robustness, production security, load capacity or every MLflow UI interaction. Human review should inspect the explanations and the suggested actions as well as the green rows.

## Read the rendered lessons

Download the `showroom-preview` artifact from the successful `showroom-docs` check on [review PR #98](https://github.com/rhpds/agent-antipatterns-lab/pull/98). Open `modules/module-02-model-interface.html` through `modules/module-07-running-it-for-real.html`. The preview contains instructions and code without executing them. The local portable review package also includes HTML views of the executed notebooks, their original files and the evidence index so review does not require a running cluster. CI preview artifacts contain rendered instructions, not those live executions.

The existing temporary Showroom still follows `test`; this review branch is not published there until it is reviewed and promoted. A CI preview, a live notebook execution and a published Showroom are different artifacts.

## Verification

The implementation passed all 109 fast CI tests with the disposable pgvector database. Focused tests also verified the strengthened gateway citation assertion. Final-head CI status and the exact-source Showroom preview are linked from PR #98. Both live test registrations were restored to their original project data. The MLflow UI route reaches the expected authentication entry point; manual UI/content review remains open.

## Separate deployment and release work

Fresh catalog provisioning and effective owner approval on `main` remain tracked in [release PR #96](https://github.com/rhpds/agent-antipatterns-lab/pull/96). The restart repair in [PR #97](https://github.com/rhpds/agent-antipatterns-lab/pull/97) and reset safety repair in [PR #99](https://github.com/rhpds/agent-antipatterns-lab/pull/99) passed independent code review and merged into `test`. The review branch includes both repairs; its lesson notebooks, module pages and model-facing solution code are unchanged from content snapshot `063acb2`.

The lab author reviews the module content first. The designated release reviewer then reviews promotion from `test` to `main`. Operational code review into `test` does not substitute for either content review or release approval. [Implementation provenance](../implementation-provenance.md) records the automated contributions.
