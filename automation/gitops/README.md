# GitOps charts

| Chart | Scope | Installs |
|---|---|---|
| `bootstrap-infra` | once per cluster | operators, OpenShift AI (unless `rhoai.install: false`), GPU, the two vLLM endpoints, MLflow, MCP Gateway |
| `bootstrap-tenant` | once per participant (`username`) | the `<username>-app` namespace, RBAC, pgvector, the workbench |

## Values files for `bootstrap-infra`

- `values.yaml`: the event layout (one 4× L40S node).
- `values-dev-single-l4.yaml`: a dev cluster with one L4. Only one endpoint runs at a time.
- `values-ai-workloads.yaml`: add this when the RHDP `ai_workloads` role installs OpenShift AI.

## What the Argo CD Application for `bootstrap-tenant` needs

Verified by syncing a real tenant Application on OpenShift GitOps 1.22.1 (Argo CD), OpenShift AI 3.5.1, 2026-10-14.

**Server-side diff, including mutation webhooks.** The OpenShift AI notebook webhook adds the auth proxy container, MLflow and CA-bundle env, and volumes to the workbench Notebook. With the default client-side diff, the Notebook stays `OutOfSync` and automated self-heal re-applies it every few minutes, forever. Set this on the **Application**; OpenShift GitOps 1.22 ignores it on the resource:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/compare-options: ServerSideDiff=true,IncludeMutationWebhook=true
```

With it, the tenant Application goes `Synced/Healthy` and stays there. An untested alternative: `ignoreDifferences` on the Notebook's `/spec/template/spec/containers` and `/spec/template/spec/volumes`. It hides more of the Notebook from comparison.

A working Application, as used for the check:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: lab-tenant-user1
  namespace: openshift-gitops
  annotations:
    argocd.argoproj.io/compare-options: ServerSideDiff=true,IncludeMutationWebhook=true
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/rhpds/agent-antipatterns-lab.git
    targetRevision: main
    path: automation/gitops/bootstrap-tenant
    helm:
      valuesObject:
        username: user1
        deployer:
          domain: <cluster apps domain>
  destination:
    server: https://kubernetes.default.svc
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

The chart itself orders its sync waves so that a sync completes on a `WaitForFirstConsumer` storage class: each PersistentVolumeClaim is in the same wave as the pod that mounts it.
