"""Optional MLflow tracing.

In the lab workbench, OpenShift AI's MLflow integration sets MLFLOW_TRACKING_URI and
MLFLOW_TRACKING_AUTH=kubernetes-namespaced, so this works with no setup. Elsewhere, set
MLFLOW_TRACKING_URI to a Route to the MLflow server including the /mlflow path it is
mounted under, plus MLFLOW_WORKSPACE (a namespace) and MLFLOW_TRACKING_TOKEN; the
mlflow client reads all of them from the environment. When MLFLOW_TRACKING_URI is not
set, every function here does nothing, so the agent runs fine without MLflow.
"""
import contextlib
import json
import os
import pathlib

_mlflow = None  # the mlflow module once tracing is switched on
_run_tags = {}  # tags for the next run's trace (see set_run_tags)
_experiment_id = None  # the experiment traces go to, once init() has set it
_trace_id = None  # the trace of the run that just finished (see record_run)
_model_id = None  # the MLflow agent version every trace is linked to (see init)
NAMESPACE_FILE = pathlib.Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")


def init():
    """Switch tracing on if MLFLOW_TRACKING_URI is set. Never raises."""
    global _mlflow, _experiment_id, _model_id
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
        experiment = mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "kestrel-agent"))
        _experiment_id = experiment.experiment_id
        _mlflow = mlflow
        _model_id = _set_agent_version(mlflow)
        return True
    except Exception as exc:  # tracing must never break the agent; report() says so at the end
        if os.environ.get("MLFLOW_LOGGING_LEVEL", "").upper() == "DEBUG":
            print(f"[tracing] disabled: {exc}")
        return False


def _set_agent_version(mlflow):
    """Label every trace from here on with the agent version (see version.py), for example
    kestrel-m4-start, as an MLflow agent version. Returns its id, or None if it can't be
    told (not a git checkout) or recorded; traces are recorded either way."""
    try:
        import version
        name = version.current()
        return mlflow.set_active_model(name=name).model_id if name else None
    except Exception as exc:
        if os.environ.get("MLFLOW_LOGGING_LEVEL", "").upper() == "DEBUG":
            print(f"[tracing] agent version not recorded: {exc}")
        return None


def enabled():
    """True once init() has switched tracing on."""
    return _mlflow is not None


def last_trace_id():
    """The trace of the run that just finished, or None when none was recorded."""
    return _trace_id


def forget_last_trace():
    """Before a new run, so last_trace_id() can't return an earlier run's trace."""
    global _trace_id
    _trace_id = None


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


def _token_usage(response):
    """The call's token counts in MLflow's form, or None when the model reported none (MLflow
    then shows no total rather than a misleading 0)."""
    usage = getattr(response, "usage", None)
    counts = {"input_tokens": getattr(usage, "prompt_tokens", None),
              "output_tokens": getattr(usage, "completion_tokens", None),
              "total_tokens": getattr(usage, "total_tokens", None)}
    if any(not isinstance(n, int) for n in counts.values()):
        return None
    return counts


def record_model_call(span, response):
    """Put what the model returned on its span, where the trace view shows it: the stop
    reason, the tool calls it made (an empty list when it made none), and its text. The
    call's token counts go on the span too; MLflow totals them for the trace, which is the
    Tokens column in the trace list (module 3: a loop costs more than a run that stops)."""
    try:
        choice = response.choices[0]
        calls = [{"name": c.function.name, "arguments": c.function.arguments}
                 for c in (choice.message.tool_calls or [])]
        attributes = {"finish_reason": choice.finish_reason, "tool_call_count": len(calls)}
        usage = _token_usage(response)
        if usage:
            attributes["mlflow.chat.tokenUsage"] = usage
        span.set_attributes(attributes)
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
    global _trace_id
    try:
        span.set_outputs({"answer": summary["answer"], "ended_by": summary["ended_by"],
                          "turns": summary["turns"], "tool_call_count": len(summary["tool_calls"])})
        if _mlflow is not None:
            _trace_id = _mlflow.get_active_trace_id()
            if _run_tags:
                _mlflow.update_current_trace(tags=dict(_run_tags))
    except Exception as exc:
        print(f"[tracing] run outcome not recorded: {exc}")


def trace_url(base, experiment_id, trace_id, workspace=None):
    """The MLflow address that opens one trace, in the participant's workspace if known."""
    workspace_part = f"workspace={workspace}&" if workspace else ""
    return f"{base.rstrip('/')}/#/experiments/{experiment_id}/traces?{workspace_part}selectedEvaluationId={trace_id}"


def evaluation_url(run_id):
    """The MLflow address that opens an evaluation run, or None when there's no UI address."""
    uri = os.environ.get("MLFLOW_TRACKING_URI", "")
    ui = os.environ.get("LAB_MLFLOW_UI_URL") or (uri if uri.startswith(("http://", "https://")) else None)
    if not (ui and run_id and _experiment_id):
        return None
    workspace = _workspace()
    workspace_part = f"workspace={workspace}&" if workspace else ""
    return f"{ui.rstrip('/')}/#/experiments/{_experiment_id}/evaluation-runs?{workspace_part}selectedRunUuid={run_id}"


def _workspace():
    """OpenShift AI's MLflow keeps each project's experiments in that project's workspace."""
    if os.environ.get("MLFLOW_WORKSPACE"):
        return os.environ["MLFLOW_WORKSPACE"]
    try:
        return NAMESPACE_FILE.read_text().strip() or None
    except OSError:
        return None


def report(summary):
    """After a run: print where its trace is, or that none was recorded, and note the link
    in the run's summary.json. Prints nothing when tracing is off. Never raises."""
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        return None
    try:
        recorded = (_mlflow is not None and _trace_id is not None
                    and _mlflow.get_trace(_trace_id) is not None)
    except Exception:
        recorded = False
    if not recorded:
        print("No trace recorded: MLflow couldn't be reached. "
              "The payloads are saved; see them with: python payloads.py")
        return None
    ui = os.environ.get("LAB_MLFLOW_UI_URL") or (uri if uri.startswith(("http://", "https://")) else None)
    where = trace_url(ui, _experiment_id, _trace_id, _workspace()) if ui else f"{_trace_id} (in {uri})"
    print(f"Trace in MLflow: {where}")
    try:
        path = pathlib.Path(summary["run_dir"]) / "summary.json"
        record = json.loads(path.read_text())
        record.update({"trace_id": _trace_id, "trace_url": where if ui else None})
        path.write_text(json.dumps(record, indent=2))
    except Exception:
        pass
    return where


def log_evaluation(name, params, cases, counts):
    """Record the module 7 regression set as an MLflow evaluation run called `name`.

    `cases` is [(trace_id, status, reason)] for each case that recorded a trace. Each trace
    gets the case's PASS, FAIL or SKIP, with the reason, as its "check" assessment: the same
    verdict the terminal printed, from the same deterministic check (no LLM judge). The run
    also keeps the passed, failed and skipped counts as metrics, and is linked to the agent
    version. Returns the run id, or None when tracing is off or nothing could be recorded."""
    if _mlflow is None or not cases:
        return None
    try:
        import contextlib
        import io
        from mlflow.entities import Feedback
        from mlflow.genai.scorers import scorer

        verdicts = {trace_id: (status, reason) for trace_id, status, reason in cases}

        @scorer(name="check")
        def check(trace):
            status, reason = verdicts[trace.info.trace_id]
            return Feedback(value=status, rationale=reason)

        # One case at a time, like the regression loop itself (the default is 10 workers).
        os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "1")
        data = [{"trace": _mlflow.get_trace(trace_id)} for trace_id in verdicts]
        with _mlflow.start_run(run_name=name) as run:
            # evaluate() prints its own banner and progress; the regression output has enough.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                _mlflow.genai.evaluate(data=data, scorers=[check], model_id=_model_id)
            _mlflow.log_params(params)
            _mlflow.log_metrics(counts)
            return run.info.run_id
    except Exception as exc:
        print(f"[tracing] evaluation not recorded: {exc}")
        return None
