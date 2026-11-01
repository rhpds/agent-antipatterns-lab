"""Optional MLflow tracing.

In the lab workbench, OpenShift AI's MLflow integration sets MLFLOW_TRACKING_URI and
MLFLOW_TRACKING_AUTH=kubernetes-namespaced, so this works with no setup. Elsewhere, set
MLFLOW_TRACKING_URI to a Route to the MLflow server including the /mlflow path it is
mounted under, plus MLFLOW_WORKSPACE (a namespace) and MLFLOW_TRACKING_TOKEN; the
mlflow client reads all of them from the environment. When MLFLOW_TRACKING_URI is not
set, every function here does nothing, so the agent runs fine without MLflow.
"""
import contextlib
import os

_mlflow = None  # the mlflow module once tracing is switched on
_run_tags = {}  # tags for the next run's trace (see set_run_tags)


def init():
    """Switch tracing on if MLFLOW_TRACKING_URI is set. Never raises."""
    global _mlflow
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        return False
    try:
        # Send each trace before the process exits; this is a short-lived CLI.
        os.environ.setdefault("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "false")
        # Fail fast if the server is unreachable instead of retrying for minutes.
        os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
        os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "5")
        import logging
        import mlflow

        # MLflow's INFO lines ("Experiment ... does not exist. Creating a new experiment.")
        # read like errors to a participant on the first run; keep only its warnings,
        # unless MLFLOW_LOGGING_LEVEL asks for something else.
        if not os.environ.get("MLFLOW_LOGGING_LEVEL"):
            logging.getLogger("mlflow").setLevel(logging.WARNING)
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "kestrel-agent"))
        _mlflow = mlflow
        return True
    except Exception as exc:  # tracing must never break the agent
        print(f"[tracing] disabled: {exc}")
        return False


class _NoSpan:
    def set_inputs(self, *a, **k): pass
    def set_outputs(self, *a, **k): pass
    def set_attributes(self, *a, **k): pass


@contextlib.contextmanager
def span(name, span_type="UNKNOWN", inputs=None):
    """Open a trace span. A no-op when tracing is off or the span cannot start."""
    if _mlflow is None:
        yield _NoSpan()
        return
    try:
        cm = _mlflow.start_span(name=name, span_type=span_type)
        live = cm.__enter__()
        if inputs is not None:
            live.set_inputs(inputs)
    except Exception as exc:
        print(f"[tracing] span {name!r} skipped: {exc}")
        yield _NoSpan()
        return
    try:
        yield live
    except BaseException as exc:
        cm.__exit__(type(exc), exc, exc.__traceback__)
        raise
    else:
        cm.__exit__(None, None, None)


def record_model_call(span, response):
    """Put what the model returned on its span, where the trace view shows it: the stop
    reason, the tool calls it made (an empty list when it made none), and its text."""
    try:
        choice = response.choices[0]
        calls = [{"name": c.function.name, "arguments": c.function.arguments}
                 for c in (choice.message.tool_calls or [])]
        span.set_attributes({"finish_reason": choice.finish_reason, "tool_call_count": len(calls)})
        span.set_outputs({"finish_reason": choice.finish_reason, "tool_calls": calls,
                          "content": choice.message.content})
    except Exception as exc:
        print(f"[tracing] model call not recorded: {exc}")


def set_run_tags(**tags):
    """Tag the next run's trace with what varied, for example endpoint and prompt, so the
    MLflow trace list can show and filter runs by them."""
    _run_tags.clear()
    _run_tags.update({k: str(v) for k, v in tags.items()})


def record_run(span, summary):
    """Put the run's outcome on the root span: the answer, why the run ended, how many
    turns it took, and how many tools it actually called."""
    try:
        span.set_outputs({"answer": summary["answer"], "ended_by": summary["ended_by"],
                          "turns": summary["turns"], "tool_call_count": len(summary["tool_calls"])})
        if _mlflow is not None and _run_tags:
            _mlflow.update_current_trace(tags=dict(_run_tags))
    except Exception as exc:
        print(f"[tracing] run outcome not recorded: {exc}")


def log_baseline(name, params, metrics):
    """Record a named run (module 7 baseline). No-op when tracing is off."""
    if _mlflow is None:
        return None
    try:
        with _mlflow.start_run(run_name=name) as run:
            _mlflow.log_params(params)
            _mlflow.log_metrics(metrics)
            return run.info.run_id
    except Exception as exc:
        print(f"[tracing] baseline not recorded: {exc}")
        return None
