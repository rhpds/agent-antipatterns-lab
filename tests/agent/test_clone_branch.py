"""Each environment clones the lab from the branch its catalog item deploys from (#88).

David, 2026-11-02: the test environment clones test, the event clones main, and dev is only
the explicit default for dev environments. Both runtime clones (the participant's workbench
and the module 6 lab tool server) read one setting, labRepoRef, which the catalog passes
alongside the branch it deploys. With no setting, rendering stops with the reason instead
of quietly cloning dev.
"""
import subprocess

import pytest
import yaml

from test_module6_own_gateway import CHARTS, helm, of_kind, render

TENANT_DEV = CHARTS / "bootstrap-tenant" / "values-dev.yaml"
INFRA_DEV = CHARTS / "bootstrap-infra" / "values-dev-single-l4.yaml"


def workbench_ref(docs):
    (notebook,) = of_kind(docs, "Notebook")
    (setup,) = notebook["spec"]["template"]["spec"]["initContainers"]
    return {e["name"]: e.get("value") for e in setup["env"]}["LAB_REPO_REF"]


def tool_server_ref(docs):
    deployment = next(d for d in of_kind(docs, "Deployment") if d["metadata"]["name"] == "mcp-server")
    (clone,) = deployment["spec"]["template"]["spec"]["initContainers"]
    script = clone["args"][0]
    branch = script.split("--branch", 1)[1].split()[0]
    return branch.strip("'\"")


@pytest.mark.parametrize("branch", ["test", "main"])
def test_each_environment_clones_its_own_branch(branch):
    """The workbench and the tool server clone the branch the environment's catalog passes."""
    assert workbench_ref(render("bootstrap-tenant", f"labRepoRef={branch}")) == branch
    assert tool_server_ref(render("bootstrap-infra", f"labRepoRef={branch}")) == branch


def test_dev_is_the_explicit_default_for_dev_environments_only():
    """dev comes only from the dev values files, never from the charts' own defaults."""
    for chart in ("bootstrap-tenant", "bootstrap-infra"):
        assert not yaml.safe_load((CHARTS / chart / "values.yaml").read_text()).get("labRepoRef")
    assert yaml.safe_load(TENANT_DEV.read_text())["labRepoRef"] == "dev"
    assert yaml.safe_load(INFRA_DEV.read_text())["labRepoRef"] == "dev"
    tenant = render("bootstrap-tenant", files=[TENANT_DEV])
    assert workbench_ref(tenant) == "dev"
    infra = render("bootstrap-infra", "mcpGateway.enabled=true", files=[INFRA_DEV])
    assert tool_server_ref(infra) == "dev"


@pytest.mark.parametrize("chart", ["bootstrap-tenant", "bootstrap-infra"])
def test_without_a_branch_rendering_stops_with_the_reason(chart):
    """No quiet fallback to dev: an environment that doesn't say its branch fails to render."""
    out = subprocess.run([helm(), "template", "t", str(CHARTS / chart), "--set", "deployer.domain=apps.example.com"],
                         capture_output=True, text=True)
    assert out.returncode != 0
    assert "labRepoRef" in out.stderr
