"""MLflow tracing is optional and must never break a run."""
import pytest

from conftest import read_json


def test_tracing_records_spans_when_uri_set(work, tmp_path):
    mlflow = pytest.importorskip("mlflow")
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    work.repoint_to_validated()
    work.apply_solution("module-03")
    summary, _ = work.agent("m3", env={"MLFLOW_TRACKING_URI": uri})
    assert summary["turns"] == 3
    mlflow.set_tracking_uri(uri)
    exp = mlflow.get_experiment_by_name("kestrel-agent")
    traces = mlflow.search_traces(locations=[exp.experiment_id], return_type="list")
    assert len(traces) == 1
    spans = {s.name: s for s in traces[0].data.spans}
    assert {"agent_run", "model_call_1", "model_call_3", "find_part", "check_stock"} <= set(spans)
    assert spans["model_call_1"].attributes["finish_reason"] == "tool_calls"
    assert spans["model_call_3"].attributes["finish_reason"] == "stop"
    # The evidence is in the spans' inputs and outputs, not only in attributes (#58).
    assert spans["model_call_1"].inputs["tools_offered"] == ["find_part", "check_stock"]
    assert [c["name"] for c in spans["model_call_1"].outputs["tool_calls"]] == ["find_part"]
    assert spans["model_call_3"].outputs["tool_calls"] == []
    assert spans["model_call_3"].outputs["finish_reason"] == "stop"
    root = spans["agent_run"].outputs
    assert root["turns"] == 3 and root["tool_call_count"] == len(summary["tool_calls"]) > 0


def test_unreachable_tracking_server_does_not_break_the_agent(work):
    summary, _ = work.agent("m1", env={"MLFLOW_TRACKING_URI": "http://127.0.0.1:9"})
    assert summary["turns"] == 1


def test_regression_records_named_baseline_in_mlflow(work, tmp_path):
    mlflow = pytest.importorskip("mlflow")
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    work.repoint_to_validated()
    out = work.run("regression.py", "--name", "my-baseline", env={"MLFLOW_TRACKING_URI": uri}).stdout
    assert "Recorded MLflow run 'my-baseline'" in out
    mlflow.set_tracking_uri(uri)
    runs = mlflow.search_runs(experiment_names=["kestrel-agent"], output_format="list")
    assert [r.info.run_name for r in runs] == ["my-baseline"]
    assert runs[0].data.metrics["skipped"] == 3
