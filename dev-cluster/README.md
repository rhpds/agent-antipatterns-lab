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
`guardrailsorchestrator`, `mcp-gateway`.

`mock-target` is a ~30-line stdlib-only OpenAI-compatible HTTP server used as
a stand-in target for Garak, NeMo Guardrails, and MCP Gateway testing, so this
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
- **MCP Gateway** needed nine separate fixes to get a working end-to-end
  request through — see the comments in `manifests/mcp-*.yaml` for the "why"
  behind each one:
  1. Backends must live in `openshift-ingress` or `redhat-ods-applications`
     (the shared Gateway's namespace allow-list) — not an arbitrary project.
  2. Kuadrant CR must be created by hand to bootstrap Authorino/Limitador.
  3. `MCPGatewayExtension` → Gateway needs a `ReferenceGrant` in
     `openshift-ingress`.
  4. `MCPGatewayExtension` needs `spec.publicHost` set — this Gateway's
     listener has no hostname of its own.
  5. Session-store Secret needs the `mcp.kuadrant.io/secret=true` label and a
     **real Redis** connection string (`memory://` panics the broker).
  6. Redis needs to run on port 8081, not 6379 — `redhat-ods-applications`'s
     default NetworkPolicy only opens a fixed port list. Also needs
     `--protected-mode no`.
  7. That same NetworkPolicy also blocks the broker's own gRPC ext_proc port
     (50051) — this is what actually causes end-to-end requests to hang and
     504 with `ext_proc_error_per-message_timeout_exceeded`, even after every
     CR reports Ready. Check the *Gateway's* Envoy access log
     (`openshift-ingress`), not the broker pod's log — the broker never sees
     the request.
  8. Upstream MCP servers must implement the `ping` method or the broker
     marks them unhealthy and silently drops their tools.
  9. Tools need an `id` field alongside `name` (broker-specific extension
     beyond the vanilla MCP spec); `MCPServerRegistration.userSpecificList`
     requires `spec.prefix` to be set.

  Identity-based tool filtering (Round 2's actual demo) works via a
  mechanism worth knowing about directly: the Gateway's own OAuth proxy
  forwards the caller's Kubernetes identity to upstream MCP servers as
  `X-Auth-Request-User`. `mock-mcp-server.py` uses that header to return a
  different tool list per caller — no custom AuthPolicy needed for the
  simple case.

## Known limitation

The `redhat-ods-applications` Secret this creates
(`rh1-mcp-session-store`) triggered a permission prompt under Claude Code's
auto-mode classifier the first time (secret write to a shared namespace not
explicitly named in the request) — expect that same prompt if you drive this
through an agent rather than running the script directly.
