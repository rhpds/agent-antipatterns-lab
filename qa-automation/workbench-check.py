"""Executed over oc exec stdin, using the workbench's own identity and services.

Notebook execution uses nbclient. Evidence and isolated checkouts stay on the PVC;
only verdicts and paths return to the coordinator. Participant edits stay untouched.
"""
import contextlib
import io
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

REPO = Path("/opt/app-root/src/agent-antipatterns-lab")
ARTIFACT = None


def git(*args, cwd=REPO):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def catalog():
    import agent
    import toolbox
    config = agent.load_config()
    config["tools"]["gateway_url"] = os.environ["LAB_GATEWAY_URL"]
    return [tool["function"]["name"] for tool in toolbox.open_toolbox(config).definitions]


def readiness():
    for endpoint in ("a", "b"):
        url = f"http://qwen3-8b-{endpoint}-predictor.llm-serving.svc:8080/v1/models"
        with urllib.request.urlopen(url, timeout=30) as response:
            assert json.load(response)["data"], "Serving endpoint has no model"
    import psycopg
    with psycopg.connect(connect_timeout=10) as connection:
        assert connection.execute("SELECT count(*) FROM bulletins").fetchone()[0] >= 12, "Bulletin corpus is incomplete"
    import tracing
    assert tracing.init(), "Authenticated MLflow initialization failed"
    names = catalog()
    assert all(any(n.endswith(tool) for n in names) for tool in ("find_part", "check_stock", "search_bulletins")), "Gateway catalog is incomplete"
    return {"services": ["models", "pgvector", "mlflow", "gateway"]}


STRICT_SHELL = '''
import labnb as lab
_shell = get_ipython()
_system = _shell.system
def _checked_system(command):
    _system(command)
    if _shell.user_ns.get('_exit_code', 0):
        raise RuntimeError('Notebook shell command failed')
_shell.system = _checked_system
_sh = lab.sh
def _checked_sh(command):
    result = _sh(command)
    if result:
        raise RuntimeError('Notebook helper command failed')
    return result
lab.sh = _checked_sh
'''


def verify_module(number, root):
    agent_dir = root / "agent"
    sys.path.insert(0, str(agent_dir))
    import regression
    summaries = [json.loads(p.read_text()) for p in sorted((agent_dir / "runs").glob("*/summary.json"))]
    assert summaries, "Notebook produced no agent run records"
    assert all(s.get("trace_url") for s in summaries), "A required run has no recorded MLflow trace"
    calls = lambda summary, suffix: [t for t in summary["tool_calls"] if t["name"].endswith(suffix)]
    first, last = summaries[0], summaries[-1]
    if number == 1:
        assert first["ended_by"] == "plain_answer" and not first["tool_calls"], "Module 1 starting failure was not demonstrated"
        response = json.loads(next((agent_dir / "runs").glob("*/01-response.json")).read_text())
        assert "<tool_call>" in response["choices"][0]["message"]["content"], "Stranded tool call evidence is missing"
    elif number == 2:
        assert len(summaries) == 3 and not first["tool_calls"] and not summaries[1]["tool_calls"], "Mismatched/strong-prompt failure is missing"
        assert calls(last, "find_part"), "Validated endpoint did not fire the tool"
        verdict, reason = regression.check_m1(last, 6)
        assert verdict == "PASS", reason
    elif number == 3:
        assert first["ended_by"] == "max_turns", "Looping starting failure is missing"
        assert last["ended_by"] == "stop" and calls(last, "find_part") and calls(last, "check_stock"), "Fixed loop did not finish correctly"
        verdict, reason = regression.check_m3(last, 6)
        assert verdict == "PASS", reason
    elif number == 4:
        assert not any(t["result"].get("category") == "bad_request" for t in first["tool_calls"]), "Starting tool error was already fixed"
        assert any(t["result"].get("category") == "bad_request" for t in summaries[1]["tool_calls"]), "Fixed tool did not expose the bad request"
        verdict, reason = regression.check_m4(summaries[1], 6)
        assert verdict == "PASS", reason
    elif number == 5:
        assert not calls(first, "search_bulletins"), "Starting state already has retrieval"
        hits = calls(summaries[1], "search_bulletins")
        assert any(p["source"] == "SB-2024-102" for t in hits for p in t["result"].get("data", {}).get("passages", [])), "F-21 retrieval source is missing"
        assert "SB-2024-102" in summaries[1]["answer"], "Grounded answer omitted its citation"
        assert any(t["result"].get("category") == "no_results" for t in calls(last, "search_bulletins")), "Out-of-corpus result is not an explicit miss"
    elif number == 6:
        for summary in summaries[:2]:
            verdict, reason = regression.check_m3(summary, 6)
            assert verdict == "PASS", reason
        # The model may also check the seal kit. Compare the requested pump's facts,
        # rather than treating an additional valid tool call as a failed lesson.
        results = lambda summary: sorted(json.dumps(t["result"], sort_keys=True)
                                         for t in calls(summary, "check_stock")
                                         if t["arguments"].get("part_number") == "KI-CP-40817"
                                         and t["arguments"].get("depot") == "Denver")
        assert results(summaries[0]) == results(summaries[1]), "Gateway pump-stock results differ from the participant's local tools"
        assert not calls(summaries[-2], "estimate_delivery"), "Tool was visible before registration"
        assert any(t["result"].get("data", {}).get("transit_days") == 1 for t in calls(last, "estimate_delivery")), "New tool was not discovered and used"
    else:
        config = __import__("agent").load_config()
        assert len(summaries) == 6, "Regression did not produce all six cases"
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for summary, (_, _, check) in zip(summaries, regression.CASES):
            verdict, _ = check(summary, config["agent"]["max_turns"])
            counts[verdict] += 1
        assert counts == {"PASS": 6, "FAIL": 0, "SKIP": 0}, "Regression did not pass every case"
        return {"regression": counts}
    return {}


def module(number):
    import nbformat
    from nbclient import NotebookClient

    directory = Path(tempfile.mkdtemp(prefix="lb8000-e2e-", dir=REPO.parent))
    global ARTIFACT
    ARTIFACT = directory / "executed.ipynb"
    root = directory / "repo"
    subprocess.run(["git", "clone", "--local", "--no-hardlinks", str(REPO), str(root)],
                   check=True, capture_output=True)
    notebook_path = next((root / "notebooks").glob(f"module-{number:02d}-*.ipynb"))
    notebook = nbformat.read(notebook_path, as_version=4)
    original_ids = {cell.id for cell in notebook.cells if cell.cell_type == "code"}
    notebook.cells.insert(0, nbformat.v4.new_code_cell(STRICT_SHELL))
    # These are the manual config edits in the module 2 and 6 instructions.
    target = {2: "module-02-23", 6: "module-06-12"}.get(number)
    if target:
        edit = ("from pathlib import Path\np = Path('config.toml')\n"
                "p.write_text(p.read_text().replace('qwen3-8b-a-predictor', 'qwen3-8b-b-predictor'))") if number == 2 else (
                "import json, os\nfrom pathlib import Path\np = Path('config.toml')\n"
                "p.write_text(p.read_text().replace('gateway_url = \"\"', 'gateway_url = ' + json.dumps(os.environ['LAB_GATEWAY_URL']), 1))")
        index = next(i for i, cell in enumerate(notebook.cells) if cell.id == target)
        notebook.cells.insert(index, nbformat.v4.new_code_cell(edit))
    client = NotebookClient(notebook, timeout=900, kernel_name="python3",
                            resources={"metadata": {"path": str(root / "notebooks")}})
    try:
        client.execute()
    finally:
        nbformat.write(notebook, ARTIFACT)
    evidence = verify_module(number, root)
    if number == 7:
        text = "\n".join(str(output.get("text", "")) for cell in notebook.cells for output in cell.get("outputs", []))
        recorded = re.search(r"Recorded MLflow run 'my-baseline' \(([\w-]+)\)", text)
        assert recorded, "Module 7 did not record its MLflow evaluation"
        import tracing
        import mlflow
        assert tracing.init(), "Cannot verify the recorded MLflow evaluation"
        run = mlflow.get_run(recorded.group(1))
        assert all(run.data.metrics.get(key) == value for key, value in {"passed": 6, "failed": 0, "skipped": 0}.items()), "Recorded evaluation counts differ from regression results"
        rows = mlflow.search_traces(run_id=run.info.run_id, return_type="list")
        assert len(rows) == 6 and all(any(a.name == "check" and a.value == "PASS" for a in trace.info.assessments) for trace in rows), "MLflow must retain six passing case assessments"
        evidence["evaluation_id"] = run.info.run_id
    evidence.update(module=number, code_cells=len(original_ids),
                    executed_cells=sum(c.cell_type == "code" and c.id in original_ids and c.execution_count is not None for c in notebook.cells),
                    artifact=str(ARTIFACT))
    return evidence


if __name__ == "__main__":
    result = {"status": "FAIL"}
    try:
        assert git("rev-parse", "HEAD") == sys.argv[2], "Workbench checkout does not match the selected release"
        phase = sys.argv[1]
        # Libraries may log details; expose only the explicit verdict below.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            if phase == "module":
                result.update(module(int(sys.argv[3])))
            else:
                sys.path.insert(0, str(REPO / "agent"))
                result.update(readiness() if phase == "readiness" else {"tools": catalog()})
        result.update(status="PASS", commit=sys.argv[2])
    except Exception as error:
        result["reason"] = str(error) if isinstance(error, AssertionError) else type(error).__name__
        if ARTIFACT and ARTIFACT.exists():
            result["artifact"] = str(ARTIFACT)
    print("LB8000_EVIDENCE=" + json.dumps(result))
    sys.exit(0 if result["status"] == "PASS" else 1)
