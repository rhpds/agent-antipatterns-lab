# dev-cluster

Repeatable, resource-optimized deploy/teardown for verifying the RH1 lab's
RHOAI components on the homelab SNO dev cluster. This is **not** the delivered
lab content — it's scaffolding for the lab author to confirm a component
installs and functions before writing it into a module.

The cluster runs at ~90%+ requested CPU even at idle (single Ryzen 9 5900X
node carrying the full RHOAI stack). Every instance deployed here has a real
cost, so:

- `deploy.sh` applies pre-tuned resource requests from the start — no
  after-the-fact patching needed.
- `teardown.sh` gives it all back when you're done. Run it between work
  sessions, not just at the end of the project.

## Usage

```bash
export KUBECONFIG=~/.kube/sno.kubeconfig
./deploy.sh                      # everything
./deploy.sh mlflow evalhub       # just these
./teardown.sh                    # back to operators-only baseline
```

Components: `mock-target`, `mlflow`, `nemoguardrails`, `evalhub`,
`guardrailsorchestrator`.

`mock-target` is a ~30-line stdlib-only OpenAI-compatible HTTP server used as
a stand-in target for Garak and NeMo Guardrails testing, so this
scaffolding never has to touch the real (and separately broken)
`vllm-toolcall-test` CPU-vLLM experiment.

## Gotchas already fixed in these manifests

Found the hard way during 2026-08-19 verification — full narrative in
`publishing-house/worklog.yaml` entries `2026-08-19-020` through `-023`.

- **MLflow CR is a cluster-wide singleton.** Name must be literally `mlflow`;
  it always lands in `redhat-ods-applications` regardless of the CR's own
  namespace. Default 1-CPU request doesn't fit this node — tuned down.
- **MLflow RHOAIENG-44516 workaround** (Gateway rejects k8s tokens): Route
  direct to the Service + a required `X-MLflow-Workspace: <namespace>` header.
  Could not reproduce the Gateway rejection with a plain SA token on 3.4.3 —
  worth re-testing with a real workbench token before relying on that.
- **MLflow RHOAIENG-45969** (artifact serving not auto-configured):
  `serveArtifacts` + `artifactsDestination` must be set explicitly; then
  `log_artifact` works fine.
- **NeMoGuardrails** needs a ConfigMap key named exactly `config.yaml` (not
  `.yml`) and a `rails.co` Colang file even with zero custom Colang logic, or
  the server hard-fails at startup. Image is 7.2GB — budget pull time.
- **GuardrailsOrchestrator** hard-requires a real KServe
  `ServingRuntime`/`InferenceService` — fails cleanly with "no ServingRuntimes
  found" otherwise. Same GPU/vLLM dependency as Round 1; can't be functionally
  verified until `vllm-toolcall-test`'s `/hfcache` permission bug is fixed.
- **EvalHub/Garak** REST API needs k8s RBAC on `trustyai.opendatahub.io`
  providers/collections/jobs/evaluations (plus `mlflow.kubeflow.org`
  experiments/runs/artifacts if MLflow tracking is wired in) and a required
  `X-Tenant: <namespace>` header. Use the `quick` benchmark id for anything
  live/timed — collections like `quality`/`avid` pull in probes (e.g.
  `atkgen.Tox`) that run their own local attack-generator model per turn and
  take 100-235s/turn on CPU.
