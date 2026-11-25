"""Each environment clones the lab from the branch its catalog item deploys from (#88).

David, 2026-11-02: the test environment clones test, the event clones main, and dev is only
the explicit default for dev environments. The runtime clone (the participant's workbench)
reads one setting, labRepoRef, which the catalog passes alongside the branch it deploys.
With no setting, rendering stops with the reason instead of quietly cloning dev.
"""
import subprocess

import pytest
import yaml

from charts import CHARTS, helm, of_kind, render

TENANT_DEV = CHARTS / "bootstrap-tenant" / "values-dev.yaml"


def workbench_ref(docs):
    (notebook,) = of_kind(docs, "Notebook")
    (setup,) = notebook["spec"]["template"]["spec"]["initContainers"]
    return {e["name"]: e.get("value") for e in setup["env"]}["LAB_REPO_REF"]


@pytest.mark.parametrize("branch", ["test", "main"])
def test_each_environment_clones_its_own_branch(branch):
    """The workbench clones the branch the environment's catalog passes."""
    assert workbench_ref(render("bootstrap-tenant", f"labRepoRef={branch}")) == branch


def test_dev_is_the_explicit_default_for_dev_environments_only():
    """dev comes only from the dev values file, never from the chart's own default."""
    assert not yaml.safe_load((CHARTS / "bootstrap-tenant" / "values.yaml").read_text()).get("labRepoRef")
    assert yaml.safe_load(TENANT_DEV.read_text())["labRepoRef"] == "dev"
    tenant = render("bootstrap-tenant", files=[TENANT_DEV])
    assert workbench_ref(tenant) == "dev"


def test_without_a_branch_rendering_stops_with_the_reason():
    """No quiet fallback to dev: an environment that doesn't say its branch fails to render."""
    out = subprocess.run([helm(), "template", "t", str(CHARTS / "bootstrap-tenant"), "--set", "deployer.domain=apps.example.com", "--set", "username=user1"],
                         capture_output=True, text=True)
    assert out.returncode != 0
    assert "labRepoRef" in out.stderr
