# RHDP provisioning repair

**Goal:** Repair the existing two-user workshop and commit the deployment contract and regression checks that prevent its source and identity failures from recurring.

**Architecture:** Reuse the existing Helm charts, Argo CD Applications and OpenShift operators. Keep the approved acceptance in `acceptance/lab/provisioning.feature`. Add a narrow release-content preflight using Git, resolve participant identity from either an explicit username or RHDP's existing tenant metadata, and supply an overlay for RHDP-managed OpenShift AI and GPUs. Never replace installed platform operators or expose application Helm values containing credentials.

**Tech stack:** Helm, Python/pytest, Git, OpenShift CLI, Argo CD, existing GitHub CI.

## Steps

- [x] Commit the two scenarios approved by David before implementation.
- [ ] Add failing tests in `tests/agent/test_provisioning_contract.py`: the September revision is rejected for missing charts; the current release contains charts, agent and notebooks; two RHDP tenant identities produce separate namespaces/workbenches/RBAC; explicit identities remain supported; missing/conflicting identities fail clearly; existing operators are not installed again by the RHDP overlay.
- [ ] Run `.venv/bin/python -m pytest tests/agent/test_provisioning_contract.py -q` and observe meaningful failures before implementing the changes.
- [ ] Implement the participant helper in `automation/gitops/bootstrap-tenant/templates/_helpers.tpl`, use it in namespace/RBAC/database/workbench templates, and remove the unsafe default participant identity. Update existing test fixtures to supply identities explicitly.
- [ ] Add `gpu.install` alongside the existing `rhoai.install` switch, use it in operator/operand/wait templates, and add a RHDP overlay that reuses installed GPU, NFD, cert-manager and OpenShift AI operators. Make the DataScienceCluster wait query the v2 resource explicitly, matching the CR this chart creates.
- [ ] Add `automation/gitops/check-release.py`, reuse Git to check selected revisions for both charts and the runtime/notebook content, and run it in CI. Document the exact RHDP source/identity/overlay contract and the requirement that provisioning failures are fatal in the owning catalog.
- [ ] Enable the installed DataScienceCluster's MLflow v2 component after a server dry run. Preserve its other component settings.
- [ ] Verify Helm renders, acceptance bindings, full agent tests where available, documentation checks and the complete change diff. Commit changes and push a reviewable feature branch.
- [ ] Correct the live Argo Applications with matching candidate source/runtime refs, reuse-installed-platform values and the two real tenant identities. Preserve their existing Helm values and credentials without printing them. Monitor operator installation and every application sync; diagnose subsequent concrete failures before changing anything further.
- [ ] Verify both participant workbenches, model endpoints, MLflow and gateway, including real module regression behavior. Record exact evidence and remaining limitations.
- [ ] Prepare the catalog-owner correction against `rhpds/agnosticv`; that repository currently returns HTTP 404 to this authenticated account. Do not claim the durable catalog pin is changed until its actual source is corrected and verified.

## Known live evidence

The three Applications point at the September 14 commit `48c0397` (one through a misleading October tag); neither chart directory exists there. The cluster has four allocatable GPUs and all 34 OpenShift operators are available and not degraded. OpenShift AI 3.5.3 is installed, the MLflow component is absent, and RHDP passes each participant under `tenant.user.name` rather than the chart's expected top-level `username`. The existing GPU/NFD OperatorGroups have different names from this chart's defaults, so a second install must be avoided.
