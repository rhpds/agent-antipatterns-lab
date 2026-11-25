"""The live test entry point must fail honestly before an environment is ready."""
import json
import os
import runpy
import subprocess
import sys
from types import SimpleNamespace

from conftest import REPO


def test_live_checks_without_environment_write_failure_report(tmp_path):
    """Scenario: Incomplete testing cannot be mistaken for success"""
    output = tmp_path / "evidence"
    env = {key: value for key, value in os.environ.items() if not key.startswith("LB8000_")}
    result = subprocess.run([sys.executable, str(REPO / "qa-automation/run.py"),
                             "--output", str(output)], cwd=REPO,
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert (output / "report.json").exists(), result.stderr
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "FAIL"
    assert "LB8000_KUBECONFIG" in report["reason"]
    assert len(report["modules"]) == 6
    assert all(row["status"] == "INCOMPLETE" for row in report["modules"])


def test_module_cannot_be_ready_when_its_documentation_check_failed(tmp_path, monkeypatch):
    runner = runpy.run_path(str(REPO / "qa-automation/run.py"))
    output = tmp_path / "evidence"
    monkeypatch.setattr(sys, "argv", ["run.py", "--output", str(output)])
    for key, value in {"LB8000_KUBECONFIG": "unused", "LB8000_PARTICIPANTS": "alice,bob",
                       "LB8000_RELEASE": "a" * 40}.items():
        monkeypatch.setenv(key, value)

    def failed_docs(args, **kwargs):
        from pathlib import Path
        junit = Path(args[args.index("--junitxml") + 1])
        junit.write_text('<testsuite><testcase name="test_readiness[0]"/><testcase name="test_readiness[1]"/>'
                         '<testcase name="test_module[0-module-01]"><properties><property name="runtime" '
                         'value="{&quot;artifact&quot;:&quot;/workbench/executed.ipynb&quot;}"/></properties></testcase>'
                         '<testcase name="test_module[1-module-01]"/>'
                         '<testcase name="test_each_module_is_ready_for_david_to_review"><failure message="mirror mismatch"/>'
                         '</testcase></testsuite>')
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(subprocess, "run", failed_docs)
    assert runner["main"]() == 1
    report = json.loads((output / "report.json").read_text())
    assert report["modules"][0]["status"] != "PASS"
    assert report["modules"][0]["evidence"][0].get("runtime") == {"artifact": "/workbench/executed.ipynb"}
