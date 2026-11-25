"""Render the lab's GitOps charts with helm, for the tests that check what they would deploy.

helm must be installed (CI's runner image has it). A check that can't run fails, not skips.
"""
import os
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO

CHARTS = REPO / "automation" / "gitops"


def helm():
    path = os.environ.get("HELM") or shutil.which("helm")
    if not path:
        pytest.fail("helm is not installed, so the charts can't be checked")
    return path


def render(chart, *sets, files=()):
    """Render a chart. Each environment must say which branch the workbench clones
    (labRepoRef, #88); unless the call sets it or passes values files, render as the test
    environment."""
    args = [helm(), "template", "t", str(CHARTS / chart), "--set", "deployer.domain=apps.example.com"]
    for f in files:
        args += ["-f", str(f)]
    if chart == "bootstrap-tenant" and not files and not any(s.startswith("labRepoRef=") for s in sets):
        sets = (*sets, "labRepoRef=test")
    if chart == "bootstrap-tenant" and not any(s.startswith(("username=", "tenant.user.name=")) for s in sets):
        sets = (*sets, "username=user1")
    for s in sets:
        args += ["--set", s]
    out = subprocess.run(args, check=True, capture_output=True, text=True).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def of_kind(docs, kind):
    return [d for d in docs if d.get("kind") == kind]
