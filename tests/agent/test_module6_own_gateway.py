"""Module 6's gateway stands apart from OpenShift AI's (acceptance/lab/module6-own-gateway.feature).

These render the lab's charts with helm and check what they would deploy. The failure they
guard against was seen live on 2026-11-02: MCP Gateway's extension puts a filter first on every
request through the Gateway it targets, and on OpenShift AI's data-science-gateway that returned
404 for MLflow, the dashboard and workbenches. The live check is that those pages still answer
with the lab's gateway installed; these tests keep the charts from pointing back at OpenShift
AI's Gateway.

helm must be installed (CI's runner image has it). A check that can't run fails, not skips.
"""
import json
import os
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO

CHARTS = REPO / "automation" / "gitops"
OPENSHIFT_AI_GATEWAY = "data-science-gateway"


def helm():
    path = os.environ.get("HELM") or shutil.which("helm")
    if not path:
        pytest.fail("helm is not installed, so the gateway charts can't be checked")
    return path


def render(chart, *sets, files=()):
    """Render a chart. Each environment must say which branch it clones (labRepoRef, #88);
    unless the call sets it or passes values files, render as the test environment."""
    args = [helm(), "template", "t", str(CHARTS / chart), "--set", "deployer.domain=apps.example.com"]
    for f in files:
        args += ["-f", str(f)]
    if not files and not any(s.startswith("labRepoRef=") for s in sets):
        sets = (*sets, "labRepoRef=test")
    for s in sets:
        args += ["--set", s]
    out = subprocess.run(args, check=True, capture_output=True, text=True).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def of_kind(docs, kind):
    return [d for d in docs if d.get("kind") == kind]


def one(docs, kind):
    found = of_kind(docs, kind)
    assert len(found) == 1, f"expected one {kind}, found {len(found)}"
    return found[0]


@pytest.fixture(scope="module")
def infra():
    return render("bootstrap-infra")


def gateway_refs(docs):
    """(kind, name, the Gateway it points at) for everything that attaches to a Gateway."""
    refs = []
    for d in of_kind(docs, "HTTPRoute"):
        refs += [("HTTPRoute", d["metadata"]["name"], p["name"]) for p in d["spec"]["parentRefs"]]
    for d in of_kind(docs, "MCPGatewayExtension"):
        refs.append(("MCPGatewayExtension", d["metadata"]["name"], d["spec"]["targetRef"]["name"]))
    for d in of_kind(docs, "ReferenceGrant"):
        refs += [("ReferenceGrant", d["metadata"]["name"], t.get("name"))
                 for t in d["spec"]["to"] if t["kind"] == "Gateway"]
    return refs


def test_the_lab_gateway_never_attaches_to_openshift_ai_gateway(infra):
    """Scenario: OpenShift AI's own pages keep working with the lab's gateway installed

    Nothing the lab installs attaches to OpenShift AI's Gateway, so the extension's filter can't
    sit in front of MLflow, the dashboard or the workbenches. Everything MCP attaches to the lab's
    own Gateway, which has its own GatewayClass (so its own Envoy).
    """
    refs = gateway_refs(infra)
    assert refs, "the chart rendered nothing that attaches to a Gateway"
    assert not [r for r in refs if r[2] == OPENSHIFT_AI_GATEWAY], refs

    gateway = one(infra, "Gateway")
    assert gateway["metadata"]["name"] != OPENSHIFT_AI_GATEWAY
    assert {r[2] for r in refs} == {gateway["metadata"]["name"]}
    gateway_class = one(infra, "GatewayClass")
    assert gateway["spec"]["gatewayClassName"] == gateway_class["metadata"]["name"]
    assert gateway_class["metadata"]["name"] != "data-science-gateway-class"

    extension = one(infra, "MCPGatewayExtension")
    assert extension["spec"]["targetRef"]["name"] == gateway["metadata"]["name"]
    # Only the lab's MCP namespace may attach routes to it.
    namespaces = {listener["allowedRoutes"]["namespaces"]["selector"]["matchLabels"]["kubernetes.io/metadata.name"]
                  for listener in gateway["spec"]["listeners"]}
    assert namespaces == {extension["metadata"]["namespace"]}


def test_the_lab_gateway_is_reached_from_inside_the_cluster_only(infra):
    """Scenario: The lab's gateway is reached from the workbench

    The workbench is given the Gateway's in-cluster address, the same one the extension serves,
    and nothing gives the Gateway a public address: its Service is ClusterIP and no Route points
    at it.
    """
    gateway = one(infra, "Gateway")
    name, ns = gateway["metadata"]["name"], gateway["metadata"]["namespace"]
    in_cluster = f"{name}-{gateway['spec']['gatewayClassName']}.{ns}.svc.cluster.local"

    params = gateway["spec"]["infrastructure"]["parametersRef"]
    config = [d for d in of_kind(infra, "ConfigMap") if d["metadata"]["name"] == params["name"]
              and d["metadata"]["namespace"] == ns]
    assert len(config) == 1
    assert yaml.safe_load(config[0]["data"]["service"])["spec"]["type"] == "ClusterIP"
    assert not [d for d in of_kind(infra, "Route") if name in str(d.get("spec", {}).get("to", {}))]
    assert not [d for d in of_kind(infra, "Service") if d.get("spec", {}).get("type") == "LoadBalancer"]

    assert one(infra, "MCPGatewayExtension")["spec"]["publicHost"] == in_cluster

    tenant = render("bootstrap-tenant")
    env = [e for nb in of_kind(tenant, "Notebook")
           for c in nb["spec"]["template"]["spec"]["containers"] for e in c.get("env", [])]
    urls = [e["value"] for e in env if e["name"] == "LAB_GATEWAY_URL"]
    assert urls == [f"https://{in_cluster}/mcp"]


def test_without_module_6_nothing_waits_for_or_creates_the_lab_gateway():
    """With the gateway turned off (the single-L4 dev values do this), the chart renders no lab
    Gateway, and the platform wait job doesn't wait for one, so the sync can finish."""
    docs = render("bootstrap-infra", "mcpGateway.enabled=false")
    assert not of_kind(docs, "Gateway") and not of_kind(docs, "MCPGatewayExtension")
    jobs = json.dumps(of_kind(docs, "Job"))
    assert "lab-mcp-gateway" not in jobs
    assert "oc get gateway data-science-gateway -n openshift-ingress" in jobs
