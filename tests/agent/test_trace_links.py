"""Every run points the participant at its own trace (acceptance/lab/trace-links*.feature)."""
import re

import pytest

UI = "https://mlflow.example/mlflow"   # stands in for the workbench's MLflow address
LINK = re.compile(re.escape(UI) + r"/#/experiments/(\w+)/traces\?(?:workspace=[\w-]+&)?selectedEvaluationId=(tr-[0-9a-f]+)")


def traced(tmp_path):
    return {"MLFLOW_TRACKING_URI": f"sqlite:///{tmp_path}/mlflow.db", "LAB_MLFLOW_UI_URL": UI}


def recorded_trace_ids(tmp_path):
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    exp = mlflow.get_experiment_by_name("kestrel-agent")
    return exp.experiment_id, [t.info.trace_id for t in mlflow.search_traces(locations=[exp.experiment_id], return_type="list")]


def test_a_run_links_to_its_own_trace(work, tmp_path):
    """Scenario: A run links to its own trace"""
    pytest.importorskip("mlflow")
    out = work.run("agent.py", "--q", "m1", env=traced(tmp_path)).stdout
    match = LINK.search(out)
    assert match, out
    experiment_id, trace_ids = recorded_trace_ids(tmp_path)
    assert match.group(1) == experiment_id and trace_ids == [match.group(2)]
    assert "Trace in MLflow: " in out


def test_without_tracing_nothing_about_traces_is_printed(work):
    """Scenario: Without tracing, nothing about traces is printed"""
    out = work.run("agent.py", "--q", "m1").stdout
    assert "Answer:" in out and "Payloads saved in" in out and "python payloads.py" in out
    assert "trace" not in out.lower()


def test_a_run_whose_trace_could_not_be_recorded_says_so(work):
    """Scenario: A run whose trace couldn't be recorded says so"""
    out = work.run("agent.py", "--q", "m1", env={"MLFLOW_TRACKING_URI": "http://127.0.0.1:9"}).stdout
    assert "No trace recorded: MLflow couldn't be reached." in out
    assert "see them with: python payloads.py" in out
    assert "[tracing]" not in out and "Traceback" not in out


def test_the_payloads_view_links_to_the_same_runs_trace(work, tmp_path):
    """Scenario: The payloads view links to the same run's trace"""
    pytest.importorskip("mlflow")
    run_link = LINK.search(work.run("agent.py", "--q", "m1", env=traced(tmp_path)).stdout).group(0)
    out = work.run("payloads.py").stdout
    assert f"Trace in MLflow: {run_link}" in out


def test_the_payloads_of_an_untraced_run_say_nothing_about_traces(work):
    """Scenario: The payloads of an untraced run say nothing about traces"""
    work.agent("m1")
    out = work.run("payloads.py").stdout
    assert "tools declared: ['find_part', 'check_stock']" in out and "--raw" in out
    assert "trace" not in out.lower()


def test_the_link_carries_the_participants_workspace(work):
    """Scenario: A run links to its own trace (the link opens in the participant's MLflow workspace)"""
    code = "import tracing; print(tracing.trace_url('https://h/mlflow/', '7', 'tr-abc', 'user1-app'))"
    assert work.run("-c", code).stdout.strip() == \
        "https://h/mlflow/#/experiments/7/traces?workspace=user1-app&selectedEvaluationId=tr-abc"
