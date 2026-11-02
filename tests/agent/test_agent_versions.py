"""Every trace and evaluation names the agent version behind it (acceptance/lab/mlflow-agent-versions.feature).

Versions are MLflow agent versions (logged models) named after the module start the agent's
files match, for example kestrel-m4-start, or kestrel-m4-start-modified once the participant
has edited them (David, 2026-11-02, Q6). These need a git checkout, as the workbench clone is.
"""
import shutil
import subprocess
import sys

import pytest

from conftest import AGENT, START_URL


@pytest.fixture
def checkout(tmp_path, endpoints):
    """A git checkout of agent/ whose endpoints are the mock ones, as reset.py sees them."""
    dest = tmp_path / "agent"
    shutil.copytree(AGENT, dest, ignore=shutil.ignore_patterns("runs", "__pycache__", ".reset-backup", ".lab-state"))
    config = dest / "config.toml"
    config.write_text(config.read_text().replace(START_URL, endpoints["mismatched"]))
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "starter"]):
        subprocess.run([*git, *args], cwd=dest, check=True, capture_output=True)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
           "LAB_MISMATCHED_URL": endpoints["mismatched"], "LAB_VALIDATED_URL": endpoints["validated"],
           "MLFLOW_TRACKING_URI": f"sqlite:///{tmp_path}/mlflow.db"}

    def run(*args):
        out = subprocess.run([sys.executable, *args], cwd=dest, env=env, capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stdout + out.stderr
        return out.stdout

    return dest, run, env["MLFLOW_TRACKING_URI"]


def latest_trace_version(uri):
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(uri)
    exp = mlflow.get_experiment_by_name("kestrel-agent")
    trace = mlflow.search_traces(locations=[exp.experiment_id], return_type="list",
                                 order_by=["timestamp_ms DESC"], max_results=1)[0]
    model_id = trace.info.trace_metadata.get("mlflow.modelId")
    return mlflow.get_logged_model(model_id).name if model_id else None


def test_every_trace_says_which_build_produced_it(checkout):
    """Scenario: Every trace says which build of the agent produced it"""
    dest, run, uri = checkout
    run("agent.py", "--q", "m1")
    assert latest_trace_version(uri) == "kestrel-m1-start"           # a fresh clone is module 1's start
    for module in (3, 4, 7):
        run("reset.py", str(module))
        run("agent.py", "--q", "m1")
        assert latest_trace_version(uri) == f"kestrel-m{module}-start"
    # David (Q6): after an edit, the starting version plus "modified".
    (dest / "agent.py").write_text((dest / "agent.py").read_text() + "\n# my edit\n")
    run("agent.py", "--q", "m1")
    assert latest_trace_version(uri) == "kestrel-m7-start-modified"
    run("reset.py", "4")
    run("agent.py", "--q", "m1")
    assert latest_trace_version(uri) == "kestrel-m4-start"


def test_the_evaluation_run_names_the_agent_version_it_tested(checkout):
    """Scenario: The evaluation run names the agent version it tested"""
    dest, run, uri = checkout
    run("reset.py", "5")
    run("regression.py", "--name", "m5-baseline")
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(uri)
    (summary,) = mlflow.search_runs(experiment_names=["kestrel-agent"], output_format="list")
    (model,) = mlflow.get_run(summary.info.run_id).inputs.model_inputs
    assert mlflow.get_logged_model(model.model_id).name == "kestrel-m5-start"


def test_outside_a_git_checkout_runs_are_traced_without_a_version(work, tmp_path):
    """The version needs the lab's git checkout; without one, tracing works as before."""
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    summary, _ = work.agent("m1", env={"MLFLOW_TRACKING_URI": uri})
    assert summary["turns"] == 1
    assert latest_trace_version(uri) is None
