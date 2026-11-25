"""Live acceptance only: invoke through qa-automation/run.py on a dedicated workshop.

These checks never fall back to mock services. Every missing input/service fails.
"""
import json
import base64
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def command(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=kwargs.pop("timeout", 60), **kwargs)


@pytest.fixture(scope="session")
def workshop():
    required = ("LB8000_KUBECONFIG", "LB8000_PARTICIPANTS", "LB8000_RELEASE")
    assert all(os.environ.get(key) for key in required), "Run through qa-automation/run.py with explicit lab settings"
    return {"kubeconfig": os.environ[required[0]], "participants": os.environ[required[1]].split(","),
            "commit": os.environ[required[2]], "isolation": {}}


def oc(workshop, *args):
    result = command(["oc", "--kubeconfig", workshop["kubeconfig"], "--request-timeout=20s", *args])
    assert result.returncode == 0, "OpenShift read/check failed; inspect the selected workshop"
    return result.stdout


def remote(workshop, participant, phase, *args, record_property=None):
    namespace = participant + "-app"
    result = command(["oc", "--kubeconfig", workshop["kubeconfig"], "--request-timeout=20s",
                      "exec", "-i", "-n", namespace, "kestrel-agent-0", "-c", "kestrel-agent",
                      "--", "python", "-", phase, workshop["commit"], *map(str, args)],
                     input=(ROOT / "qa-automation/workbench-check.py").read_text(), timeout=3600)
    marker = next((line.removeprefix("LB8000_EVIDENCE=") for line in result.stdout.splitlines()
                   if line.startswith("LB8000_EVIDENCE=")), None)
    assert marker is not None, f"{participant}: workbench check {phase} did not return evidence"
    evidence = json.loads(marker)
    if phase == "module" and evidence.get("artifact") and os.environ.get("LB8000_EVIDENCE_DIR"):
        path = Path(evidence["artifact"])
        assert str(path).startswith("/opt/app-root/src/lb8000-e2e-") and path.name == "executed.ipynb" and ".." not in path.parts
        relative = Path("artifacts") / participant / f"module-{int(args[0]):02d}.ipynb"
        destination = Path(os.environ["LB8000_EVIDENCE_DIR"]) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(oc(workshop, "exec", "-n", namespace, "kestrel-agent-0", "-c", "kestrel-agent", "--", "cat", str(path)))
        evidence["remote_artifact"] = str(path)
        evidence["artifact"] = str(relative)
    if record_property:
        record_property("runtime", json.dumps({**evidence, "participant": participant}))
    assert result.returncode == 0 and evidence["status"] == "PASS", evidence
    return evidence


@pytest.mark.parametrize("slot", [0, 1])
def test_readiness_means_participants_can_begin_the_lab(workshop, slot):
    """Scenario: Readiness means participants can begin the lab"""
    participant = workshop["participants"][slot]
    namespace = participant + "-app"
    notebook = json.loads(oc(workshop, "get", "notebook", "kestrel-agent", "-n", namespace, "-o", "json"))
    assert notebook["metadata"]["annotations"]["opendatahub.io/username"] == participant
    applications = oc(workshop, "get", "applications", "-n", "openshift-gitops", "-o", "json")
    audit = command([sys.executable, str(ROOT / "automation/gitops/check-release.py"), "--applications", "-"],
                    input=applications, cwd=ROOT)
    assert audit.returncode == 0, audit.stderr
    assert workshop["commit"][:12] in audit.stdout, "Applications do not select the tested release"
    selected = [app for app in json.loads(applications)["items"] if app.get("spec", {}).get("source", {}).get("path")
                in ("automation/gitops/bootstrap-infra", "automation/gitops/bootstrap-tenant")]
    # Assertions may print their operands. Never expose credential-bearing App values.
    states = [(app["metadata"]["name"], app["status"]["sync"]["status"], app["status"]["health"]["status"]) for app in selected]
    assert len(states) == 3 and all(sync == "Synced" and health == "Healthy" for _, sync, health in states), "All three lab Applications must be Synced and Healthy"
    pod = json.loads(oc(workshop, "get", "pod", "kestrel-agent-0", "-n", namespace, "-o", "json"))
    assert any(c["type"] == "Ready" and c["status"] == "True" for c in pod["status"]["conditions"])
    assert oc(workshop, "auth", "can-i", "get", "notebooks", "--as", participant, "-n", namespace).strip() == "yes"
    assert remote(workshop, participant, "readiness")["services"] == ["models", "pgvector", "mlflow"]


@pytest.mark.parametrize("module", range(1, 7), ids=lambda n: f"module-{n:02d}")
@pytest.mark.parametrize("slot", [0, 1])
def test_every_module_works_through_the_participant_instructions(workshop, slot, module, record_property):
    """Scenario: Every module works through the participant instructions"""
    participant = workshop["participants"][slot]
    evidence = remote(workshop, participant, "module", module, record_property=record_property)
    assert evidence["module"] == module
    assert evidence["code_cells"] > 0
    assert evidence["executed_cells"] == evidence["code_cells"]
    assert evidence["commit"] == workshop["commit"]
    if module == 6:
        assert evidence["regression"] == {"PASS": 5, "FAIL": 0, "SKIP": 0}
        workshop["isolation"][participant] = True


def test_participants_complete_the_lab_independently(workshop):
    """Scenario: Participants complete the lab independently"""
    assert len(set(workshop["participants"])) == 2
    assert set(workshop["isolation"]) == set(workshop["participants"]), "Both participants must complete module 6"
    # Each participant reaches only their own workbench. The lab has had no MCP Gateway, and so
    # no tool registrations to keep apart, since the 2026-11-25 scope cut.
    first, second = workshop["participants"]
    for user, other in ((first, second), (second, first)):
        # can-i exits non-zero when the answer is no, so read its answer rather than its status.
        denied = command(["oc", "--kubeconfig", workshop["kubeconfig"], "--request-timeout=20s", "auth", "can-i",
                          "get", "notebooks", "--as", user, "-n", other + "-app"])
        assert denied.stdout.strip() == "no", f"{user} can reach {other}'s workbench"


def test_each_module_is_ready_for_david_to_review(workshop):
    """Scenario: Each module is ready for David to review"""
    generated = command([sys.executable, "publishing-house/showroom/generate.py", "--check"], cwd=ROOT)
    assert generated.returncode == 0, generated.stdout + generated.stderr
    rendered = command([sys.executable, "publishing-house/showroom/verify.py", "--source-ref", workshop["commit"]], cwd=ROOT)
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    assert len(list((ROOT / "www/modules").glob("module-*.html"))) == 6


def test_the_reviewed_release_is_the_release_promoted(workshop):
    """Scenario: The reviewed release is the release promoted"""
    number = os.environ.get("LB8000_RELEASE_PR")
    assert number, "Set LB8000_RELEASE_PR to the test-to-main release PR"
    result = command(["gh", "pr", "view", number, "--repo", "rhpds/agent-antipatterns-lab",
                      "--json", "headRefOid,headRefName,baseRefName"])
    assert result.returncode == 0, "Cannot read the release PR"
    pr = json.loads(result.stdout)
    assert (pr["headRefName"], pr["baseRefName"], pr["headRefOid"]) == ("test", "main", workshop["commit"])
    protection = command(["gh", "api", "repos/rhpds/agent-antipatterns-lab/branches/main/protection"])
    assert protection.returncode == 0, "main must have enforceable branch protection"
    rules = json.loads(protection.stdout)
    assert rules["enforce_admins"]["enabled"]
    reviews = rules["required_pull_request_reviews"]
    assert reviews["dismiss_stale_reviews"]
    assert reviews["require_code_owner_reviews"]
    assert reviews["required_approving_review_count"] >= 1
    checks = set(rules["required_status_checks"]["contexts"])
    checks.update(c["context"] for c in rules["required_status_checks"].get("checks", []))
    assert {"agent-tests", "showroom-docs", "live-e2e"} <= checks
    owner = command(["gh", "api", "repos/rhpds/agent-antipatterns-lab/contents/.github/CODEOWNERS?ref=main"])
    assert owner.returncode == 0, "The required owner must already be configured on main"
    content = base64.b64decode(json.loads(owner.stdout)["content"]).decode()
    active = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
    assert active == ["* @ishuverma"], "Confirm the effective required reviewer before promotion"
