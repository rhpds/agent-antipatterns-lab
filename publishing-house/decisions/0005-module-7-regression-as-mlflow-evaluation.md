# 0005. Module 7's regression run is recorded as an MLflow evaluation

- **Status:** Accepted, 2026-11-02. David approved the scenarios that depend on it (`acceptance/lab/mlflow-regression-evaluation.feature`) and the recommended answers to their open questions.
- **Date:** 2026-11-02
- **Decided by:** David, on the agent's proposal (draft PR #79). It moves a spec boundary, so it was his to accept.
- **Affects:** module 7 (spec and content), `publishing-house/spec.yaml` and `design.md` (the AgentOps in Production boundary), `agent/regression.py`, `notebooks/labnb.py`

## Context

The spec bounds MLflow tightly. AgentOps in Production scored 99 percent overlap against
the rejected design, which had observability, metrics, tracing and evaluation modules.
After the rebuild, `spec.yaml` and `design.md` say MLflow "now appears only as the
instrument for reading a trace".

Module 7 already goes slightly past that. `regression.py --name` records an MLflow run
holding three numbers (passed, failed, skipped), and the module 7 spec calls MLflow "the
baseline store". The evidence for each case, meaning which check passed and why, lives only in
the terminal and in `runs/regression-<time>.md`. A participant who opens MLflow sees
three numbers and can't get from them to the run that failed.

MLflow 3.14, the version on the lab cluster, can record the same regression set as an
evaluation run. Each case becomes a row with its own trace and an assessment beside it,
and two evaluation runs can be compared in the UI.

## Evidence (dev cluster, OpenShift AI 3.5.2, MLflow server 3.14.0, 2026-11-02)

From throwaway runs in user1's workbench, with the 3.14.0 client pinned in #78:

- **`mlflow.genai.evaluate` with deterministic code scorers works against this server.**
  A `@scorer` returning a categorical PASS or FAIL with a rationale recorded an assessment
  on each case's trace.
- **It writes no artifacts.** The artifact list for both evaluation runs was empty, and the server's
  file artifact store has no run directories. That matters because this CR's `file://`
  artifacts with `storage` is a combination Red Hat documents as unsupported for artifact
  serving.
- **The compare view works with workspaces and kubernetes-auth.** Selecting two evaluation
  runs showed "Comparing <run> to <run>", with each question's two traces and verdicts side
  by side and a PASS/FAIL change summary.
- **Server-side judges are off.** The operator sets `MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false`
  for every deployment, so only the SDK path is available. That path is all this decision uses.

## Decision

- **`regression.py --name` records the regression set as an MLflow evaluation run.** The
  six existing checks become code scorers over each case's run record, unchanged. The
  verdicts are PASS, FAIL or SKIP, and the reason is the rationale. No LLM judge is used.
- **The evaluation run keeps the three counts** (passed, failed, skipped), logged
  explicitly, because categorical scorers log no run metrics by themselves.
- **Without tracing, nothing changes.** The terminal output and the markdown report are
  exactly what they are today.
- **The spec boundary is restated.** The current wording is: "MLflow appears only as the
  instrument for reading a trace". The new wording is: "MLflow appears as the instrument for reading a trace, and in
  module 7 as the place the regression baseline is recorded and compared. The lab
  teaches no observability or evaluation practice; no judge, metric design or
  monitoring." This restatement only names what module 7 already does with MLflow.

## Reasons

1. **The evidence is already deterministic.** The checks judge the run record, not the
   wording. This puts the same verdicts beside the traces they came from, so "judged from
   the record" is visible in the platform rather than asserted in a markdown file.
2. **A baseline is only meaningful against a later comparison.** The module 7 spec already says so.
   The compare view is that comparison, built in. Today a participant has to set two
   runs' metrics side by side and still can't see which case moved.
3. **It replaces a concept rather than adding one.** "Evaluation run" takes the place of
   "a named run on the Runs tab". Module 7's time is roughly unchanged.

## Risks and how to reverse

- **Overlap with AgentOps in Production.** This is the main risk, and the reason this is
  David's call. The guard is in what module 7 leaves out: no LLM judges, no scorer
  design exercise, no evaluation datasets, no monitoring. It records the same six checks
  the lab already has. If the RCARS overlap score moves on re-run, or a reviewer reads
  this as an evaluation module, reverse it.
- **Server load.** Thirty participants each write six traces and six assessments to one
  sqlite file behind one worker. Evaluation runs with `MLFLOW_GENAI_EVAL_MAX_WORKERS=1`,
  so it sends no more model requests than today's sequential loop.
- **Event release.** If the event ships the 3.13.0 server Red Hat documents for 3.5,
  `evaluate`, `@scorer` and the compare view all predate 3.14. Re-check them on the
  event release anyway.
- **Async trace logging.** In the same checks, one trace written with async logging
  landed as a file artifact. `tracing.py` forces synchronous logging and must keep doing
  so.
- **To reverse:** restore `tracing.log_baseline` as the only MLflow write in
  `regression.py`, and the spec sentence above.
