# 0006. The event stays on MCP Gateway 0.7.1

- **Status:** Accepted
- **Date:** 2026-11-02
- **Decided by:** David ("Keep it at 0.7.1"), on the agent's recommendation in #75
- **Affects:** module 6 (spec, notebook and content), `bootstrap-infra` (operator channels, wait job), `design.md` and `spec.yaml` maturity rows

## Context

Module 6 runs through MCP Gateway. Red Hat Connectivity Link 1.5's release notes say:
"This release includes the MCP gateway 1.0 as a Generally Available feature." Upstream,
gateway 1.0 stops serving the `mcp.kuadrant.io/v1alpha1` API. Every MCP resource the lab
creates uses that API: the `MCPGatewayExtension`, `MCPServerRegistration` and
`MCPVirtualServer`.

Red Hat's sources disagree about 1.0. The RHCL 1.5 install guide and the OpenShift AI 3.5
docs still say Technology Preview.

## Evidence (dev cluster, OpenShift AI 3.5.2, 2026-11-02)

- The Red Hat catalog's `mcp-gateway` package has one channel, `preview`, at v0.7.1. Its
  CRDs are all `v1alpha1`.
- `rhcl-operator` channel `stable-1.5` (v1.5.0) lists the gateway's images among its related
  images, but owns no MCP CRDs. A 1.0 build can't be installed and tested from the catalog.
- On 0.7.1, module 6 works end to end through the lab's own Gateway (#75). The regression set
  passes 6 of 6 through it.

## Decision

- **The event runs MCP Gateway 0.7.1 with Red Hat Connectivity Link 1.4.**
- **Provisioning checks that the installed gateway serves `v1alpha1`,** and stops with the
  reason if it doesn't, rather than letting module 6 fail later without one.
- **The lab names the version plainly:** "MCP Gateway 0.7.1 (Technology Preview); 1.0 is GA
  in Connectivity Link 1.5."
- **The move to 1.0 and `mcp.kuadrant.io/v1` is tracked in #80.**

## Reasons

1. **0.7.1 is the version that installs from Red Hat's catalog and has been tested.** No
   supported path to 1.0 has been confirmed for OpenShift yet. David has asked Red Hat how it
   is delivered.
2. **Moving early means installing from outside Red Hat's catalog.** That isn't a
   supported path for an RHDP lab.
3. **Module 6 is supporting, not load-bearing.** It carries one objective, and no other
   module's outcome depends on it.

## Risks and how to reverse

- **The spec keeps one non-GA dependency** while Red Hat's release notes call 1.0 GA. A
  reviewer may ask why. This record is the answer.
- **If the event's catalog offers only 1.0,** provisioning stops at the `v1alpha1` check. The
  migration in #80 is then needed before the event (estimated at a day on a dev cluster).
- **The check runs at provisioning only.** The operator subscription uses automatic
  approval, so a 1.0 build arriving in the `preview` channel would upgrade a running cluster
  and break module 6 there.
- **To reverse:** do #80 (install 1.0, move the manifests to `v1`, re-run the module 6
  scenarios, swap the `v1alpha1` check for a `v1` one) and update the maturity rows.
