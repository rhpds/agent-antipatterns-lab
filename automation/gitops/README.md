# GitOps charts

| Chart | Scope | Installs |
|---|---|---|
| `bootstrap-infra` | once per cluster | operators, OpenShift AI (unless `rhoai.install: false`), GPU, the two vLLM endpoints, MLflow, MCP Gateway |
| `bootstrap-tenant` | once per participant (`username`) | the `<username>-app` namespace, RBAC, pgvector, the workbench |

## Values files for `bootstrap-infra`

- `values.yaml`: the event layout (one 4× L40S node).
- `values-dev-single-l4.yaml`: a dev cluster with one L4. Only one endpoint runs at a time.
- `values-ai-workloads.yaml`: add this when the RHDP `ai_workloads` role installs OpenShift AI.

## How RHDP deploys these charts

AgnosticD's `ocp4_workload_gitops_bootstrap` role (`rhpds/core_workloads`) creates the Argo CD Applications from a fixed template:

- one Application for `bootstrap-infra`;
- one per participant for `bootstrap-tenant`, named `bootstrap-tenant-<GUID>`, in the `tenants` project.

The tenant Application template:

- uses `syncPolicy.automated` with `prune: false, selfHeal: false`, and `RespectIgnoreDifferences=true`;
- has no field for extra annotations, so its compare options can't be set per lab;
- injects `deployer.domain`, `deployer.apiUrl` and `deployer.guid` into the Helm values.

After creating it, the role's `tasks/workload.yml` runs two waits:

1. **"Wait until bootstrap ArgoCD application is healthy and synced".** It polls the Application every 10 s, up to `ocp4_workload_gitops_bootstrap_health_retries` times (default 60, so about 10 minutes), for Healthy **and** Synced. It runs with `ignore_errors: ocp4_workload_gitops_bootstrap_health_ignore`, default `true`, so when it runs out of retries the role logs the error and **carries on**.
2. After a 60 s pause, it checks only *child* Applications labelled `app.kubernetes.io/instance=<bootstrap name>`. This chart creates none, so the check passes at once.

`ocp4_workload_gitops_bootstrap_application_sync_required` and `..._health_required` appear in the role's defaults, but no task reads them.

## What the RHDP Argo CD instance needs: ignore the notebook webhook's additions

**Why.** The OpenShift AI notebook webhook adds these to the workbench Notebook, all identified by name:

- the `kube-rbac-proxy` container;
- nine env vars on the workbench container (`MLFLOW_*`, CA-bundle variables);
- the volume mounts and volumes `trusted-ca`, `runtime-images`, `kube-rbac-proxy-config` and `kube-rbac-proxy-tls-certificates`;
- `serviceAccountName`.

Argo CD counts them as drift. On a tenant Application built from RHDP's template, the Notebook stays `OutOfSync` forever, so the role's first wait never succeeds:

- **With the role's defaults,** every participant's provisioning **stalls for about 10 minutes** on that wait, logs an ignored error, and then continues. The environment works, but slower, and the Application shows `OutOfSync` permanently, which hides any real drift.
- **If the catalog sets `ocp4_workload_gitops_bootstrap_health_ignore: false`,** that wait fails and so does provisioning.

With `selfHeal: false` there is no re-apply loop; the loop only appears with self-heal on.

**The fix: one AgnosticV variable for the RHDP GitOps role** (`ocp4_workload_openshift_gitops`). It becomes the instance's `resourceIgnoreDifferences` and ignores only those named items, so the workbench container's own settings are still compared:

```yaml
ocp4_workload_openshift_gitops_ignore_differences: |
  resourceIdentifiers:
  - group: kubeflow.org
    kind: Notebook
    customization:
      jqPathExpressions:
      - .spec.template.spec.containers[] | select(.name == "kube-rbac-proxy")
      - .spec.template.spec.containers[].env[]? | select(.name | test("^(MLFLOW_K8S_INTEGRATION|MLFLOW_TRACKING_AUTH|MLFLOW_TRACKING_URI|PIP_CERT|REQUESTS_CA_BUNDLE|SSL_CERT_FILE|PIPELINES_SSL_SA_CERTS|KF_PIPELINES_SSL_SA_CERTS|GIT_SSL_CAINFO)$"))
      - .spec.template.spec.containers[].volumeMounts[]? | select(.name == "trusted-ca" or .name == "runtime-images")
      - .spec.template.spec.volumes[]? | select(.name | test("^(trusted-ca|runtime-images|kube-rbac-proxy-config|kube-rbac-proxy-tls-certificates)$"))
      - .spec.template.spec.serviceAccountName
```

**Verified** on OpenShift GitOps 1.22.1 with OpenShift AI 3.5.1, 2026-10-14, using a tenant Application copied from the role's template (`bootstrap-tenant-<guid>`, same sync policy and ignore rules):

| Instance setting | Tenant Application |
|---|---|
| none (as RHDP ships it) | `OutOfSync` / Healthy, Notebook only, permanently; 1 sync, no loop |
| the variable above, added to a live Application | `Synced` / Healthy within one refresh, stable |
| the variable above, Application created fresh | `Synced` / Healthy after 31 s, and still Synced once the workbench was running |

**Alternatives:**

- Lowering `ocp4_workload_gitops_bootstrap_health_retries` shortens the stall, but it also shortens the wait for a tenant that is still genuinely starting, and the Application still shows `OutOfSync`.
- `ocp4_workload_gitops_bootstrap_application_sync_required: false` does nothing: no task reads it.
- `argocd.argoproj.io/compare-options: ServerSideDiff=true,IncludeMutationWebhook=true` on the Application also works (verified). RHDP's Application template can't carry it, though. Argo CD reads compare options from the Application, not from the resource.

**Side effect of `RespectIgnoreDifferences=true`:** after the first sync, a later Git change to the ignored fields won't be applied. None of them is set by this chart.

## Sync waves

The chart orders its sync waves so that a sync completes on a `WaitForFirstConsumer` storage class. Each PersistentVolumeClaim is in the same wave as the pod that mounts it.
