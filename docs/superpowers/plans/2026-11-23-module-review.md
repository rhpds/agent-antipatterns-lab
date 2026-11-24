# Modules 2–7 review implementation plan

**Goal:** Give each module a clear review path backed by the approved scenarios, actual assertions and recorded two-participant executions.

**Architecture:** Keep the notebooks as the source of the Showroom mirrors. Reuse pytest, the existing regression checks and the recorded live runs; do not introduce an LLM judge or a new test framework. Keep historical evidence tied to its tested commit and distinguish editorial review from fresh provisioning and release approval.

**Execution:** Inline using the executing-plans workflow. The existing approved scenarios remain locked; request approval for any new participant behavior. Work in this isolated branch from test, preserving the separate restart-repair PR.

- [ ] Map every module 2–7 scenario to its actual assertions and saved live evidence. Read all notebook cells, mirrors and relevant tests.
- [ ] Challenge verdicts with counterexamples: wrong tool, wrong result, failed tool call and an unrelated empty result. Add failing tests before strengthening checks covered by approved scenarios.
- [ ] Re-evaluate retained live run records against stronger checks. Preserve genuine failures and report missing evidence explicitly.
- [ ] Correct instruction gaps in notebook source, regenerate mirrors and verify all code cells, diagrams, reveals and source links.
- [ ] Create docs/review/README.md with the coverage audit and six module checklists, including source links, expected observations, evidence and unresolved issues.
- [ ] Run focused tests, documentation generation checks and HTML verification. Run the full agent suite through CI with a disposable database before claiming it passes.
- [ ] Review the complete diff and durable review artifacts, open a review PR to test and verify its checks. Keep catalog/fresh-provision and main-policy dependencies separate from this goal's review verdicts.

## Commands

Use the existing project-local Python environment and documentation dependencies from the original checkout, without global installs. Run pytest against this worktree's tests; build this worktree's site with the pinned Antora CLI. Record exact commands and results in the review audit. Read-only extraction of saved run summaries must use only the run paths listed in the retained report, never credentials or participant configuration files.
