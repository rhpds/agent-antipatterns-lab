"""Regression coverage for the actual RHDP source/identity failures seen on 2026-11-23."""
import json
import subprocess
import sys

import pytest

from conftest import REPO
from test_clone_branch import tool_server_ref, workbench_ref
from test_module6_own_gateway import CHARTS, helm, of_kind, render

PREFLIGHT = REPO / "automation/gitops/check-release.py"
RHDP = CHARTS / "bootstrap-infra/values-rhdp.yaml"


def preflight(ref):
    return subprocess.run([sys.executable, str(PREFLIGHT), ref], cwd=REPO, capture_output=True, text=True)


def test_a_new_workshop_uses_deployable_lab_sources():
    """Scenario: A new workshop uses deployable lab sources"""
    current = preflight("HEAD")
    assert current.returncode == 0, current.stdout + current.stderr
    old = preflight("48c039717d87c4ffe2d4f2f19bbb7f07d3df0b60")
    assert old.returncode != 0
    assert "missing required lab content" in old.stderr
    assert "automation/gitops/bootstrap-infra/Chart.yaml" in old.stderr
    for ref in ("test", "dev", "rh1-2027-test-lb8000-2026-11-02"):
        assert workbench_ref(render("bootstrap-tenant", f"labRepoRef={ref}")) == ref
        assert tool_server_ref(render("bootstrap-infra", f"labRepoRef={ref}")) == ref


def test_each_participant_gets_their_own_workbench():
    """Scenario: Each participant gets their own workbench"""
    for username in ("user-zgrkm", "user-zkz8t"):
        docs = render("bootstrap-tenant", f"tenant.user.name={username}")
        (notebook,) = of_kind(docs, "Notebook")
        assert notebook["metadata"]["namespace"] == f"{username}-app"
        assert notebook["metadata"]["annotations"]["opendatahub.io/username"] == username
        bindings = of_kind(docs, "RoleBinding")
        users = {s["name"] for b in bindings for s in b["subjects"] if s["kind"] == "User"}
        assert users == {username}
        # The serving-viewer RoleBinding belongs in the shared model namespace.
        assert {d["metadata"]["namespace"] for d in docs if "namespace" in d["metadata"]} == {f"{username}-app", "llm-serving"}


def test_explicit_username_still_works():
    docs = render("bootstrap-tenant", "username=explicit-user")
    assert of_kind(docs, "Notebook")[0]["metadata"]["namespace"] == "explicit-user-app"


@pytest.mark.parametrize("settings", [[], ["username=alice", "tenant.user.name=bob"]])
def test_missing_or_conflicting_identity_stops_rendering(settings):
    args = [helm(), "template", "t", str(CHARTS / "bootstrap-tenant"), "--set", "labRepoRef=test"]
    for setting in settings:
        args += ["--set", setting]
    out = subprocess.run(args, capture_output=True, text=True)
    assert out.returncode != 0
    assert "participant identity" in out.stderr


def test_rhdp_overlay_reuses_installed_operators_and_keeps_serving():
    docs = render("bootstrap-infra", "labRepoRef=test", files=[RHDP])
    packages = {d["spec"]["name"] for d in of_kind(docs, "Subscription")}
    assert not packages.intersection({"rhods-operator", "nfd", "gpu-operator-certified", "openshift-cert-manager-operator"})
    assert packages == {"rhcl-operator", "mcp-gateway"}
    assert not of_kind(docs, "DataScienceCluster")
    assert not of_kind(docs, "ClusterPolicy")
    assert not of_kind(docs, "NodeFeatureDiscovery")
    assert of_kind(docs, "InferenceService")
    assert of_kind(docs, "MLflow")
    waits = {j["metadata"]["name"]: j["spec"]["template"]["spec"]["containers"][0]["args"][0]
             for j in of_kind(docs, "Job")}
    assert '"nvidia-gpu-operator gpu-operator-certified"' not in waits["wait-for-operators"]
    assert "gpus_allocatable" in waits["wait-for-platform"]
    assert "datascienceclusters.v2.datasciencecluster.opendatahub.io" in waits["wait-for-platform"]


@pytest.mark.parametrize("runtime_ref,expected", [("test", 0), ("HEAD", 1), ("48c039717d87c4ffe2d4f2f19bbb7f07d3df0b60", 1), ("", 1)])
def test_live_application_preflight_rejects_mixed_or_missing_runtime_release(runtime_ref, expected):
    app = {"metadata": {"name": "bootstrap-infra"}, "spec": {"source": {
        "repoURL": "https://github.com/rhpds/agent-antipatterns-lab.git",
        "targetRevision": "origin/test", "path": "automation/gitops/bootstrap-infra",
        "helm": {"parameters": [{"name": "labRepoRef", "value": runtime_ref}]},
    }}}
    out = subprocess.run([sys.executable, str(PREFLIGHT), "--applications", "-"], cwd=REPO,
                         input=json.dumps({"items": [app]}), capture_output=True, text=True)
    assert out.returncode == expected, out.stdout + out.stderr
    if expected:
        assert "labRepoRef" in out.stderr


def test_application_parse_errors_do_not_disclose_inline_values():
    app = {"spec": {"source": {
        "repoURL": "https://github.com/rhpds/agent-antipatterns-lab.git",
        "targetRevision": "HEAD", "path": "automation/gitops/bootstrap-infra",
        "helm": {"values": "password: [SECRET-TEST-MARKER"},
    }}}
    out = subprocess.run([sys.executable, str(PREFLIGHT), "--applications", "-"], cwd=REPO,
                         input=json.dumps(app), capture_output=True, text=True)
    assert out.returncode == 1
    assert "SECRET-TEST-MARKER" not in out.stdout + out.stderr
    assert "invalid Helm values" in out.stderr


def test_runtime_clone_requires_a_branch_or_tag_even_when_commits_match():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    app = {"spec": {"source": {
        "repoURL": "https://github.com/rhpds/agent-antipatterns-lab.git",
        "targetRevision": commit, "path": "automation/gitops/bootstrap-infra",
        "helm": {"parameters": [{"name": "labRepoRef", "value": commit}]},
    }}}
    out = subprocess.run([sys.executable, str(PREFLIGHT), "--applications", "-"], cwd=REPO,
                         input=json.dumps(app), capture_output=True, text=True)
    assert out.returncode == 1
    assert "labRepoRef" in out.stderr
