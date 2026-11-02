"""A trace shows what a run cost (acceptance/lab/mlflow-token-usage.feature).

The model's token counts go on each model-call span, and MLflow totals them for the trace,
which is the Tokens column in the trace list. The mock model reports counts that grow with
the request, as a real one does, so a run that loops costs more than one that stops.
"""
import pathlib
import sys

import pytest

AGENT = pathlib.Path(__file__).resolve().parents[2] / "agent"


def traces(uri):
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(uri)
    exp = mlflow.get_experiment_by_name("kestrel-agent")
    return mlflow.search_traces(locations=[exp.experiment_id], return_type="list", order_by=["timestamp_ms ASC"])


def total_tokens(trace):
    return (trace.info.token_usage or {}).get("total_tokens")


def test_the_looping_run_shows_its_token_total(work, tmp_path):
    """Scenario: The looping run's trace shows what it cost"""
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    work.repoint_to_validated()
    summary, _ = work.agent("m3", env={"MLFLOW_TRACKING_URI": uri})
    assert summary["ended_by"] == "max_turns"                    # the module 3 starting loop
    (trace,) = traces(uri)
    calls = [s for s in trace.data.spans if s.name.startswith("model_call_")]
    assert len(calls) == summary["turns"] == 6
    per_call = [s.attributes["mlflow.chat.tokenUsage"]["total_tokens"] for s in calls]
    assert all(n > 0 for n in per_call)
    assert total_tokens(trace) == sum(per_call)                  # what the trace list shows


def test_the_fixed_loop_costs_less_than_the_looping_one(work, tmp_path):
    """Scenario: The fixed loop costs less than the looping one"""
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    work.repoint_to_validated()
    work.agent("m3", env={"MLFLOW_TRACKING_URI": uri})
    work.apply_solution("module-03")
    summary, _ = work.agent("m3", env={"MLFLOW_TRACKING_URI": uri})
    assert summary["ended_by"] == "stop"
    looping, fixed = traces(uri)
    assert 0 < total_tokens(fixed) < total_tokens(looping)


def test_counts_appear_in_mlflow_only_not_the_terminal(work, tmp_path):
    """David, 2026-11-02 (Q2): the token counts are in MLflow, not printed in the terminal."""
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    work.repoint_to_validated()
    out = work.run("agent.py", "--q", "m3", env={"MLFLOW_TRACKING_URI": uri}).stdout
    assert "token" not in out.lower()


def test_a_model_that_reports_no_counts_leaves_the_total_empty(tmp_path, monkeypatch):
    """David, 2026-11-02 (Q1): with no counts from the model, the trace shows none (not a 0)
    and the call is otherwise recorded as before."""
    mlflow = pytest.importorskip("mlflow")
    monkeypatch.chdir(tmp_path)   # MLflow writes any local artifacts under the cwd
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path}/mlflow.db")
    monkeypatch.syspath_prepend(str(AGENT))
    sys.modules.pop("tracing", None)
    import tracing
    assert tracing.init()

    class Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    response = Obj(usage=None, choices=[Obj(finish_reason="stop",
                                            message=Obj(tool_calls=None, content="done"))])
    with tracing.span("agent_run", "AGENT"):
        with tracing.span("model_call_1", "CHAT_MODEL") as span:
            tracing.record_model_call(span, response)
    (trace,) = traces(f"sqlite:///{tmp_path}/mlflow.db")
    call = next(s for s in trace.data.spans if s.name == "model_call_1")
    assert "mlflow.chat.tokenUsage" not in call.attributes
    assert call.outputs["finish_reason"] == "stop" and call.outputs["content"] == "done"
    assert not total_tokens(trace)
    sys.modules.pop("tracing", None)
    mlflow.set_tracking_uri("")
