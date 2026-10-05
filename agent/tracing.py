"""Optional MLflow tracing.

Set MLFLOW_TRACKING_URI to a direct Route to the MLflow server (not the OpenShift
AI Gateway, which rejects Kubernetes tokens: RHOAIENG-44516). When it is not set,
every function here does nothing, so the agent runs fine without MLflow.
"""
import contextlib
import os

_mlflow = None  # the mlflow module once tracing is switched on


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
        import mlflow

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
