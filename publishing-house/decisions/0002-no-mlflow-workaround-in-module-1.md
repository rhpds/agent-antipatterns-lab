# 0002. Module 1 does not teach the MLflow authentication workaround

- **Status:** Accepted
- **Date:** 2026-10-14
- **Decided by:** the agent driving LB8000 decisions, on David's delegation. David can overturn it.
- **Affects:** module 1 (spec and content), `design.md` authoring constraints, `bootstrap-tenant` workbench

## Context

`design.md` and the module 1 spec required module 1 to document a workaround for two
known issues:

- **RHOAIENG-44516:** Kubernetes tokens are not accepted through the OpenShift AI
  Gateway, so `MLFLOW_TRACKING_URI` was to point at a direct Route.
- **RHOAIENG-45969:** S3-backed artifact serving isn't configured by the automatic
  workbench integration.

Both were taken from known-issue notes and had not been tried on a real cluster.

## Evidence (OpenShift AI 3.5.1, dev cluster, 2026-10-14)

- **The gateway accepted a workbench service-account token.** From inside a workbench
  pod, `GET <gateway>/mlflow/api/2.0/mlflow/experiments/get-by-name` with the pod's own
  token and `X-MLFLOW-WORKSPACE: user1-app` returned 200. The direct Route returned
  the same.
- **OpenShift AI's own workbench integration sets tracing up with no participant
  action** (#27). With the dashboard's `opendatahub.io/mlflow-instance` annotation on
  the Notebook, the notebook webhook injects:
  - `MLFLOW_TRACKING_URI`, the gateway's `/mlflow` URL;
  - `MLFLOW_TRACKING_AUTH=kubernetes-namespaced`;
  - `MLFLOW_K8S_INTEGRATION=true`.

  The controller binds the workbench service account to
  `mlflow-operator-mlflow-integration`.
- **A full trace was logged from inside a real workbench.** The module 3 fixed run made
  7 spans, in state OK, with only the platform's binding in place.
- **The webhook removes any hand-set `MLFLOW_TRACKING_URI`** from a Notebook without
  the annotation. So the direct-Route workaround can't even be set the documented way
  in a dashboard-shaped workbench.
- **The agent logs no artifacts.** `tracing.py` uses traces, `log_params` and
  `log_metrics` only, so RHOAIENG-45969 doesn't touch the lab.

The "workspace" failure seen on 2026-10-13 (#15) was a missing `/mlflow` path in the
tracking URI (#21), not RHOAIENG-44516.

## Decision

- **Module 1 teaches no MLflow workaround.** The workbench arrives with tracing on, and
  participants run the agent and open the trace.
- **The authoring constraint in `design.md` and the infrastructure note in the module 1
  spec are rewritten** to say this, and to keep the evidence that the issue didn't
  reproduce.
- **`bootstrap-infra` keeps the direct `mlflow` Route** as a maintainer convenience for
  tracing from outside the cluster (`agent/README.md`, "Outside a workbench"). No
  participant step uses it.

## Reasons

1. **The issue doesn't reproduce on the version the lab runs.** Teaching a workaround
   for a problem participants won't hit spends module 1 minutes on a detour. Module 1
   is 12 minutes and carries the mass-login event.
2. **The platform-native path is the better lesson for this audience.** Technical
   sellers should see OpenShift AI's MLflow integration working as shipped, not an
   exception path.
3. **The workaround would no longer work as documented.** The webhook strips a hand-set
   tracking URI.

## Risks and how to reverse

- **If RHOAIENG-44516 returns on the release the event runs,** the gateway URI the
  webhook injects would fail with the service-account token. Tracing then disables
  itself and the agent still runs, because `tracing.py` never raises.
- **The fallback is already built:** the direct Route plus `MLFLOW_TRACKING_URI`,
  `MLFLOW_WORKSPACE` and `MLFLOW_TRACKING_TOKEN`, documented in `agent/README.md`.
  Re-check on the event release during the final GPU validation.
- **To reverse:** restore the module 1 infrastructure note and the `design.md`
  constraint from before this record, and set the variables in the workbench instead
  of the annotation.
