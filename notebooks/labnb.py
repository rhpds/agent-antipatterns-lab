"""Helpers the lab's module notebooks share. Standard library only: the notebook kernel is the
workbench image's Python, which doesn't have the agent's packages (the agent itself runs in its
own virtualenv through `!python ...` cells).

Everything here reads what the agent saved under agent/runs/, so the notebooks show the same
evidence as `python payloads.py`, and links straight to the matching page in MLflow or the
OpenShift console.
"""
import datetime
import html
import json
import os
import pathlib
import tomllib
from urllib.parse import urlparse

from IPython.display import HTML, Markdown, display

AGENT = pathlib.Path(__file__).resolve().parent.parent / "agent"
RUNS = AGENT / "runs"
NAMESPACE_FILE = pathlib.Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
# Runs are folders named by their start time (runlog.py). Tables show only the runs made since
# this notebook started, so an earlier module's runs don't appear in this one's evidence.
STARTED = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


# --- where things are ---------------------------------------------------------------------

def config():
    return tomllib.loads((AGENT / "config.toml").read_text())


def namespace():
    """The participant's project, which is also their MLflow workspace."""
    if os.environ.get("MLFLOW_WORKSPACE"):
        return os.environ["MLFLOW_WORKSPACE"]
    try:
        return NAMESPACE_FILE.read_text().strip()
    except OSError:
        return None


def mlflow_home():
    """The MLflow address the workbench's OpenShift AI integration set, if any."""
    uri = os.environ.get("MLFLOW_TRACKING_URI", "")
    return uri.rstrip("/") if uri.startswith(("http://", "https://")) else None


def apps_domain():
    """The cluster's apps domain, read from the MLflow address (https://rh-ai.<apps domain>/mlflow)."""
    host = urlparse(mlflow_home() or "").hostname or ""
    return host.split(".", 1)[1] if "." in host else None


def console_url(path):
    domain = apps_domain()
    return f"https://console-openshift-console.{domain}{path}" if domain else None


def serving_runtime_url(name, ns="llm-serving"):
    """The console page with a ServingRuntime's YAML (its vLLM arguments)."""
    return console_url(f"/k8s/ns/{ns}/serving.kserve.io~v1alpha1~ServingRuntime/{name}/yaml")


_seen_experiment = None  # an experiment id learned another way (see regression)


def experiment_id():
    """The kestrel-agent experiment's id, from the newest traced run (or the regression run)."""
    if _seen_experiment:
        return _seen_experiment
    for run in reversed(runs(since_start=False)):
        trace = summary(run).get("trace_url") or ""
        if "/experiments/" in trace:
            return trace.split("/experiments/", 1)[1].split("/", 1)[0]
    return None


def experiment_url(tab="traces"):
    """The experiment's Traces (or another tab) in the participant's workspace."""
    home, eid, ws = mlflow_home(), experiment_id(), namespace()
    if not (home and eid):
        return None
    return f"{home}/#/experiments/{eid}/{tab}" + (f"?workspace={ws}" if ws else "")


def links(*items):
    """Show a short list of links: links(("label", url), ...). Missing urls are explained."""
    lines = []
    for label, url in items:
        if url:
            lines.append(f'<li><a href="{html.escape(url)}" target="_blank">{html.escape(label)}</a></li>')
        else:
            lines.append(f"<li>{html.escape(label)}: not available yet (run the agent once with tracing on)</li>")
    display(HTML("<ul>" + "".join(lines) + "</ul>"))


# --- what the agent saved -----------------------------------------------------------------

def runs(since_start=True):
    """The agent's runs, oldest first: by default only those made since this notebook started."""
    if not RUNS.exists():
        return []
    found = sorted(r for r in RUNS.glob("*") if (r / "summary.json").exists())
    return [r for r in found if r.name >= STARTED] if since_start else found


def summary(run):
    try:
        return json.loads((run / "summary.json").read_text())
    except (OSError, ValueError):
        return {}


def call(run, n=1):
    """(request, choice) of model call n, as saved; empty dicts where something is missing."""
    def load(name):
        try:
            return json.loads((run / name).read_text())
        except (OSError, ValueError):
            return {}
    request, response = load(f"{n:02d}-request.json"), load(f"{n:02d}-response.json")
    choices = response.get("choices") if isinstance(response, dict) else None
    return request, (choices[0] if choices else {})


def _endpoint(url):
    return (urlparse(url or "").hostname or "").split(".")[0].removesuffix("-predictor")


def _prompt(run):
    request, _ = call(run)
    messages = request.get("messages") or [{}]
    agent = config()["agent"]
    return {agent["system_prompt"]: "default", agent["system_prompt_strong"]: "strong"}.get(
        messages[0].get("content"), "other")


def _short(text, n=60):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _tools(s):
    out = []
    for t in s.get("tool_calls") or []:
        result = t.get("result")
        category = result.get("category") if isinstance(result, dict) else None
        out.append(t["name"] + (f" ({category})" if category else ""))
    return ", ".join(out) or "none"


def _call1_tool_calls(run):
    """tool_calls on model call 1: the names it asked for, or null / [] exactly as sent."""
    calls = (call(run)[1].get("message") or {}).get("tool_calls")
    return ", ".join(c["function"]["name"] for c in calls) if calls else json.dumps(calls)


COLUMNS = {
    "endpoint": lambda r, s: _endpoint(s.get("endpoint")),
    "prompt": lambda r, s: _prompt(r),
    "question": lambda r, s: _short(s.get("question"), 40),
    "finish_reason (call 1)": lambda r, s: call(r)[1].get("finish_reason"),
    "tool_calls (call 1)": lambda r, s: _call1_tool_calls(r),
    "turns": lambda r, s: s.get("turns"),
    "ended by": lambda r, s: s.get("ended_by"),
    "tools run": lambda r, s: _tools(s),
    "answer": lambda r, s: _short(s.get("answer")),
}


def evidence(columns=("endpoint", "turns", "ended by", "tools run", "answer"), last=8):
    """One row per agent run made in this notebook, newest last. Each run's name links to its
    trace in MLflow."""
    rs = runs()[-last:]
    if not rs:
        return display(Markdown("No runs in this notebook yet."))
    head = "".join(f"<th>{html.escape(c)}</th>" for c in ("run", *columns))
    rows = []
    for r in rs:
        s = summary(r)
        name = html.escape(r.name)
        trace = s.get("trace_url")
        cell = f'<a href="{html.escape(trace)}" target="_blank">{name}</a>' if trace else name
        values = "".join(f"<td>{html.escape(str(COLUMNS[c](r, s)))}</td>" for c in columns)
        rows.append(f"<tr><td>{cell}</td>{values}</tr>")
    display(HTML(f"<table><tr>{head}</tr>{''.join(rows)}</table>"))


def latest():
    rs = runs()
    return rs[-1] if rs else None


def content(n=1, run=None):
    """What the model returned as text on model call n of the newest run (or `run`)."""
    run = run or latest()
    if run is None:
        return display(Markdown("No runs yet."))
    text = (call(run, n)[1].get("message") or {}).get("content")
    display(Markdown(f"Run `{run.name}`, model call {n}, `content`:\n\n```text\n{'null' if text is None else text}\n```"))


def tool_results(run=None):
    """Every tool the newest run (or `run`) called, with its arguments and exactly what it returned."""
    run = run or latest()
    if run is None:
        return display(Markdown("No runs yet."))
    calls = summary(run).get("tool_calls") or []
    if not calls:
        return display(Markdown(f"Run `{run.name}` called no tools."))
    rows = "".join(
        f"<tr><td>{html.escape(t['name'])}</td><td><code>{html.escape(json.dumps(t.get('arguments')))}</code></td>"
        f"<td><code>{html.escape(json.dumps(t.get('result')))}</code></td></tr>" for t in calls)
    display(HTML(f"<p>Run <code>{html.escape(run.name)}</code>:</p><table><tr><th>tool</th>"
                 f"<th>arguments</th><th>what it returned</th></tr>{rows}</table>"))


def trace_link(run=None, label="Open this run's trace in MLflow"):
    run = run or latest()
    links((label, summary(run).get("trace_url") if run else None))


def sh(command):
    """Run a shell command in agent/ and show its output, like a `!` line, but usable inside
    Python (for example in an if-block). Uses the PATH the notebook was started with, so
    `python` is the agent's virtualenv."""
    import subprocess
    done = subprocess.run(command, shell=True, cwd=AGENT, capture_output=True, text=True)
    print(done.stdout + done.stderr, end="")
    return done.returncode


def tool_list():
    """The tool names the agent is offered right now, read the way the agent reads them
    (from the gateway when config.toml sets gateway_url)."""
    import subprocess
    code = ("import agent, toolbox; "
            "print([d['function']['name'] for d in toolbox.open_toolbox(agent.load_config()).definitions])")
    done = subprocess.run(["python", "-c", code], cwd=AGENT, capture_output=True, text=True)
    print(done.stdout + done.stderr, end="")


def run_url(run_id):
    """An MLflow run (for example the module 7 baseline), in the format MLflow itself prints."""
    home, eid, ws = mlflow_home(), experiment_id(), namespace()
    if not (home and eid and run_id):
        return None
    return f"{home}/#/experiments/{eid}/runs/{run_id}" + (f"?workspace={ws}" if ws else "")


def regression(name=None):
    """Run the module 7 regression set (optionally naming the baseline it records in MLflow),
    show its output, and link to its evaluation run in MLflow."""
    import re
    import subprocess
    command = ["python", "regression.py"] + (["--name", name] if name else [])
    done = subprocess.run(command, cwd=AGENT, capture_output=True, text=True)
    output = done.stdout + done.stderr
    keep = [line for line in output.splitlines()
            if "View run" not in line and not line.startswith("Evaluation in MLflow:")]
    print("\n".join(keep))
    global _seen_experiment
    seen = re.search(r"/experiments/(\w+)/(?:runs|evaluation-runs)\b", output)
    if seen:
        _seen_experiment = seen.group(1)
    evaluation = re.search(r"^Evaluation in MLflow: (\S+)", output, re.MULTILINE)
    recorded = re.search(r"Recorded MLflow run '[^']*' \((\w+)\)", output)
    url = evaluation.group(1) if evaluation else (run_url(recorded.group(1)) if recorded else None)
    if name:
        links((f"The evaluation run '{name}' in MLflow", url))


# --- module 6: registering a tool at the gateway ------------------------------------------

REGISTRATION_CONFIGMAP = "kestrel-tool-registrations"
SA_DIR = pathlib.Path("/var/run/secrets/kubernetes.io/serviceaccount")


def gateway_url():
    """The lab's MCP Gateway address, which the environment gives the workbench."""
    return os.environ.get("LAB_GATEWAY_URL")


def register_tool(tool="estimate_delivery"):
    """Register a tool at the gateway for this participant only: one ConfigMap in their own
    project, which the lab's tool server reads. Touches nothing in the agent."""
    import ssl
    import urllib.error
    import urllib.request
    ns = namespace()
    host, port = os.environ.get("KUBERNETES_SERVICE_HOST"), os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    if not (ns and host and (SA_DIR / "token").exists()):
        print("This isn't a lab workbench, so there's no project to register in.")
        return False
    token = (SA_DIR / "token").read_text().strip()
    ctx = ssl.create_default_context(cafile=str(SA_DIR / "ca.crt"))
    base = f"https://{host}:{port}/api/v1/namespaces/{ns}/configmaps"

    def call(method, url, body=None):
        req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": "application/merge-patch+json" if method == "PATCH"
                                              else "application/json"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return json.load(resp)

    try:
        call("PATCH", f"{base}/{REGISTRATION_CONFIGMAP}", {"data": {tool: "registered"}})
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print(f"Registration failed: HTTP {exc.code}")
            return False
        call("POST", base, {"apiVersion": "v1", "kind": "ConfigMap",
                            "metadata": {"name": REGISTRATION_CONFIGMAP},
                            "data": {tool: "registered"}})
    print(f"Registered {tool} at the gateway for project {ns}.")
    return True
