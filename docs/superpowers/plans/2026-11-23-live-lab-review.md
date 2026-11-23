# Live lab verification and review

**Goal:** Complete the approved end-to-end acceptance in `acceptance/lab/end-to-end.feature`, verify a freshly provisioned two-participant test workshop and prepare an Ishu-reviewed release to main.

**Architecture:** Keep the existing pytest suite as the deterministic CI layer. Reuse pytest for live assertions and Jupyter nbclient for executing the shipped notebook cells in the real workbench. The live layer must use the deployed model, pgvector, MLflow and gateway. Do not add an LLM judge or count mock-model results as live evidence. Wrap existing tools instead of implementing a notebook interpreter or a new test framework.

**Execution:** Sequential implementation in this feature branch, preserving existing work. The approved scenarios are committed before implementation. No automatic promotion before the review and verification gates hold.

## Ordered work and evidence

- [x] Commit the approved end-to-end criteria before implementation (`972f3b0`).
- [x] Verify baseline: all seven committed Showroom mirrors match their notebooks; four converter tests pass; main is unprotected and the repository has no rulesets.
- [ ] Finish and commit the provisioning repair, with a release audit that rejects missing chart/runtime content and mismatched refs. Re-run the targeted Helm tests and the complete agent suite. New live scenarios will initially fail the binding guard until their real tests exist; do not weaken the guard.
- [ ] Add live readiness bindings under `tests/e2e/`, using explicit kubeconfig and two participant identities. Require ready workbench pods, working model requests, queryable bulletin data, authenticated MLflow access and actual MCP tool discovery. Missing inputs/services must fail and produce an evidence report.
- [ ] Execute the shipped notebooks through nbclient in isolated checkouts on each workbench. Apply only the two edits the participant instructions require: module 2's endpoint repoint and module 6's gateway setting (including module 7's reset recovery). Preserve the original code cells and record which cells ran. Treat nonzero shell commands as errors, since notebook shell escapes do not raise by default.
- [ ] Assert the existing approved starting and completed behavior for every module from saved request/response payloads, tool results, stop conditions and traces. Require all six final regression cases PASS, zero FAIL and zero SKIP. Retain executed notebook evidence privately without credentials.
- [ ] Verify participant isolation with the real gateway before and after a single participant registers the delivery tool, then let the second participant register independently. Preserve unrelated participant work by using the dedicated test workshop.
- [ ] Replace `qa-automation/healthcheck.yml` and `e2e.yml` placeholders with entry points to the live tests. Keep fast CI independent of a live model; run live acceptance explicitly against the selected release and require its evidence for promotion.
- [ ] Build and verify all seven Showroom HTML mirrors. Generate a review index with one module row containing source and rendered-page links, exact tested commit, readiness verdict, evidence and unresolved issues. Never label incomplete or failed checks ready.
- [ ] Correct and validate candidate live Applications with consistent source/runtime refs and existing-platform overlay, preserving inline credentials. Check all operator jobs and application sync outcomes; diagnose subsequent runtime failures from actual events/logs.
- [ ] Obtain the owning AgnosticV catalog source correction, then provision and validate a fresh two-user test workshop. Live Application patches are insufficient proof of fresh provisioning. Current authenticated access to rhpds/agnosticv is HTTP 404.
- [ ] Add promotion checks on PRs to main: exact tested commit, both CI workflows, live evidence and approval from Ishu. Require dismissed approvals after changes. Confirm Ishu's GitHub account before assigning it. Inspect effective branch protection after changing it; do not infer enforcement from YAML alone.
- [ ] Open the release PR from test to main, attach the review index and verification evidence and request Ishu. Leave final promotion awaiting his approval and passing checks. Verify publication separately after a merge; a documentation build artifact alone is not a published site.

## Verification commands

```bash
.venv/bin/python -m pytest tests/agent/test_provisioning_contract.py tests/agent/test_clone_branch.py tests/agent/test_module6_own_gateway.py -q --basetemp=.cache/provisioning-contract-tests
.venv/bin/python -m pytest tests/agent -q -rs --basetemp=.cache/agent-full-tests
.venv/bin/python publishing-house/showroom/generate.py --check
.venv/bin/python -m unittest discover -s publishing-house/showroom/tests -v
npm run build:test --prefix publishing-house/showroom
.venv/bin/python publishing-house/showroom/verify.py --source-ref test
```

The binding guard and live tests must be genuinely red before implementation, then green on the actual required behavior. Run the live checks on the final source, not only a prior candidate.
