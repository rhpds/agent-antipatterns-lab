"""The lab ends with a short check of everything that was fixed
(acceptance/lab/short-closing-module.feature).

Module 6, "Running it for real", is the closing module since the 2026-11-25 scope cut. These
tests run its notebook the way a participant does: the reset cell, then every code cell in
order, against a git checkout of the agent, the mock model endpoints and a real pgvector
database. Shell lines (`!python ...`) run in the agent's folder; everything else runs with the
real labnb helpers, with IPython's display stubbed out so what it shows can be read back.
"""
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import types

import pytest

from conftest import AGENT, REPO, START_URL
from test_knowledge_and_regression import pg  # noqa: F401  (a pytest fixture)

NOTEBOOK = REPO / "notebooks" / "module-06-running-it-for-real.ipynb"
STRETCH = " (stretch goal)"
CASES = ["m1", "m3", "m4", "m5", "m5-miss"]
# What a setup step would look like: connecting the agent to something, registering a tool,
# or editing its configuration.
SETUP = re.compile(r"gateway|regist|connect|config\.toml|write_text|LAB_[A-Z_]+_URL|tool_list", re.IGNORECASE)


def cells():
    return json.loads(NOTEBOOK.read_text())["cells"]


def text(cell):
    return "".join(cell["source"])


def sections():
    """[(heading, [cells])] for each "## " section of the notebook, in order."""
    found = []
    for cell in cells():
        heading = text(cell).splitlines()[0] if cell["cell_type"] == "markdown" else ""
        if heading.startswith("## "):
            found.append((heading, []))
        if found:
            found[-1][1].append(cell)
    return found


def stretch_section():
    (section,) = [s for s in sections() if s[0].endswith(STRETCH)]
    return section


def where_next_section():
    (section,) = [s for s in sections() if s[0] == "## Where to go next"]
    return section


@pytest.fixture
def labnb(monkeypatch):
    """The notebooks' real helper module, with IPython's display replaced by a list."""
    shown = []
    display = types.ModuleType("IPython.display")
    display.HTML = display.Markdown = lambda body: body
    display.display = shown.append
    monkeypatch.setitem(sys.modules, "IPython", types.ModuleType("IPython"))
    monkeypatch.setitem(sys.modules, "IPython.display", display)
    monkeypatch.syspath_prepend(str(REPO / "notebooks"))
    sys.modules.pop("labnb", None)
    import labnb
    return labnb, shown


@pytest.fixture
def closing(tmp_path, endpoints, pg, labnb, monkeypatch):  # noqa: F811  (pg is a fixture)
    """A participant's workbench checkout with its bulletins loaded, and a way to run the
    closing module's cells in order. Tracing is off: no MLflow, as the stretch goal allows."""
    dest = tmp_path / "agent"
    shutil.copytree(AGENT, dest, ignore=shutil.ignore_patterns("runs", "__pycache__", ".reset-backup", ".lab-state"))
    config = dest / "config.toml"
    config.write_text(config.read_text().replace(START_URL, endpoints["mismatched"]))
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "starter"]):
        subprocess.run([*git, *args], cwd=dest, check=True, capture_output=True)
    # `python` in a notebook shell line is the agent's virtualenv, as in the workbench.
    monkeypatch.setenv("PATH", os.pathsep.join([os.path.dirname(sys.executable), "/usr/bin", "/bin"]))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LAB_MISMATCHED_URL", endpoints["mismatched"])
    monkeypatch.setenv("LAB_VALIDATED_URL", endpoints["validated"])
    for key, value in pg.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.chdir(dest)
    lab, shown = labnb
    monkeypatch.setattr(lab, "AGENT", dest)
    monkeypatch.setattr(lab, "RUNS", dest / "runs")
    # The lab's environment loads the bulletins before the participant starts.
    subprocess.run([sys.executable, "ingest_corpus.py"], cwd=dest, check=True, capture_output=True)

    def run_cells(skip_stretch=False):
        """Run every code cell in order (or all but the stretch goal's), as a participant would.
        Returns what the cells displayed."""
        skipped = {c["id"] for c in stretch_section()[1]} if skip_stretch else set()
        scope = {}
        for cell in cells():
            if cell["cell_type"] != "code" or cell["id"] in skipped:
                continue
            python = []
            for line in text(cell).splitlines():
                if line.lstrip().startswith("!"):
                    done = subprocess.run(line.lstrip()[1:], shell=True, cwd=dest, capture_output=True, text=True)
                    print(done.stdout + done.stderr)
                    assert done.returncode == 0, done.stdout + done.stderr
                elif not line.lstrip().startswith("%"):   # %cd ../agent: the tests already work there
                    python.append(line)
            exec("\n".join(python), scope)
        return shown

    return dest, run_cells


def regression_lines(out):
    """{case: (verdict, reason)} as the regression cell prints them."""
    return {case: (status, reason.strip()) for status, case, reason in
            re.findall(r"^(PASS|FAIL|SKIP)\s+(\S+)\s.*\n\s+(.+)$", out, re.MULTILINE)}


def checklist_rows(markdown):
    """The symptom-to-layer table's rows, as lists of cells, header and divider left out."""
    start = markdown.index("| A customer says...")
    rows = []
    for line in markdown[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def test_the_closing_module_checks_every_fix_in_one_run(closing, capsys):
    """Scenario: The closing module checks every fix in one run"""
    dest, run_cells = closing
    reset = [c for c in cells() if c["cell_type"] == "code" and "reset.py" in text(c)]
    assert [text(c).splitlines()[-1] for c in reset] == ["!python reset.py 6"]
    shown = run_cells(skip_stretch=True)
    out = capsys.readouterr().out
    assert "Ready to start module 6." in out
    verdicts = regression_lines(out)
    assert list(verdicts) == CASES                       # one row per earlier fix
    assert all(status == "PASS" and reason for status, reason in verdicts.values()), verdicts
    assert "5 passed, 0 failed, 0 skipped" in out
    # The report cell shows the newest report: the same five rows, then the checklist.
    (report,) = [s for s in shown if isinstance(s, str) and s.startswith("# Regression run")]
    for case, (status, reason) in verdicts.items():
        assert f"| {case} |" in report and f"| {status} | {reason} |" in report
    assert "## Symptom to layer" in report
    assert len(checklist_rows(report)) == 5


def test_the_closing_module_needs_no_setup_of_its_own(closing, capsys):
    """Scenario: The closing module needs no setup of its own"""
    code = [c for c in cells() if c["cell_type"] == "code"]
    for cell in code:
        assert not SETUP.search(text(cell)), f"{cell['id']} sets something up: {text(cell)}"
    # Nothing in the instructions asks for a step of the participant's own before the run,
    # and nothing between the reset and the regression cell runs anything else.
    words = [c for c in cells() if c["cell_type"] == "markdown" and c not in where_next_section()[1]]
    for cell in words:
        assert not SETUP.search(text(cell)), f"{cell['id']} asks for setup: {text(cell)}"
    order = [c["id"] for c in code]
    reset = next(c["id"] for c in code if "reset.py" in text(c))
    regression = next(c["id"] for c in code if "lab.regression(" in text(c))
    assert order.index(regression) == order.index(reset) + 1
    # Run every cell, the stretch goal's too, with nothing done in between.
    dest, run_cells = closing
    run_cells()
    assert "5 passed, 0 failed, 0 skipped" in capsys.readouterr().out


def test_comparing_runs_in_mlflow_is_optional(closing, capsys):
    """Scenario: Comparing runs in MLflow is optional"""
    heading, stretch = stretch_section()
    assert "MLflow" in heading
    assert text(stretch[0]).split("\n", 1)[1].strip().startswith("Skip this step if you're short of time.")
    all_cells = cells()
    signal = [c for c in all_cells if "**This is the module's success signal:**" in text(c)]
    assert len(signal) == 1
    assert all_cells.index(signal[0]) < all_cells.index(stretch[0])     # done before the stretch goal
    assert "mlflow" not in text(signal[0]).lower()
    # Later steps don't build on it, and the lab no longer compares runs against a baseline.
    later = all_cells[all_cells.index(stretch[-1]) + 1:]
    assert not [c for c in later if c["cell_type"] == "code"]
    assert "baseline" not in NOTEBOOK.read_text().lower()
    # Skipping it, without MLflow at all, the module still reaches its success signal.
    dest, run_cells = closing
    shown = run_cells(skip_stretch=True)
    out = capsys.readouterr().out
    assert "5 passed, 0 failed, 0 skipped" in out
    assert any(isinstance(s, str) and "## Symptom to layer" in s for s in shown)


@pytest.fixture
def regression(monkeypatch):
    monkeypatch.syspath_prepend(str(AGENT))
    return runpy.run_path(str(AGENT / "regression.py"))


def test_the_checklist_names_where_tool_access_is_governed(regression, tmp_path, capsys):
    """Scenario: The checklist names where tool access is governed"""
    main = regression["main"]
    main.__globals__["run_agent"] = lambda question, config: {
        "tool_calls": [], "tools_offered": [], "answer": "", "ended_by": "stop", "turns": 1}
    main.__globals__["RUNS_DIR"] = tmp_path
    main([])
    capsys.readouterr()
    report = next(tmp_path.glob("regression-*.md")).read_text()
    rows = checklist_rows(report)
    (governed,) = [r for r in rows if r[0] == "Who can see what?"]
    symptom, look_first, layer = governed
    assert "governed" in look_first and "platform" in look_first
    assert "next step" in layer and "no hands-on" in layer
    assert not re.search(r"\(module \d\)", layer)          # no module of the lab teaches it
    # Every other row points at the module that fixed it.
    assert [re.search(r"\(module (\d)\)", r[2]).group(1) for r in rows if r is not governed] == ["2", "3", "4", "5"]
    # The notebook's copy of the checklist is the report's, and no step of the module works on it.
    answer = next(text(c) for c in cells() if "| A customer says..." in text(c))
    assert checklist_rows(answer) == rows
    for heading, section in sections():
        if re.match(r"## \d+\. ", heading):
            assert not re.search(r"gateway|tool access", heading, re.IGNORECASE), heading
    # The module only points to it, as reading.
    where_next = "\n".join(text(c) for c in where_next_section()[1])
    assert "MCP Gateway" in where_next and "governed tool access" in where_next
    assert all(c["cell_type"] == "markdown" for c in where_next_section()[1])
