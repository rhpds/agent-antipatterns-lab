"""The notebooks' lab.show_code() shows a function from agent/ with its line numbers, and
lab.tool_results() shows each tool's arguments and result as indented JSON."""
import html
import json
import sys
import types

import pytest

from conftest import AGENT

NOTEBOOKS = AGENT.parent / "notebooks"


@pytest.fixture
def labnb(monkeypatch):
    shown = []
    display = types.ModuleType("IPython.display")
    display.HTML = display.Markdown = lambda text: text
    display.display = shown.append
    monkeypatch.setitem(sys.modules, "IPython", types.ModuleType("IPython"))
    monkeypatch.setitem(sys.modules, "IPython.display", display)
    monkeypatch.syspath_prepend(str(NOTEBOOKS))
    sys.modules.pop("labnb", None)
    import labnb
    return labnb, shown


def test_shows_a_function_with_its_own_line_numbers(labnb):
    lab, shown = labnb
    lab.show_code("tools.py", "run_tool")
    text = shown[-1]
    lines = (AGENT / "tools.py").read_text().splitlines()
    first = next(i for i, l in enumerate(lines, 1) if l.startswith("def run_tool"))
    assert f"{first}  def run_tool" in text
    assert "````python" in text and "lines" in text


def test_shows_a_top_level_name(labnb):
    lab, shown = labnb
    lab.show_code("tools.py", "TOOL_FUNCTIONS")
    assert "TOOL_FUNCTIONS = {" in shown[-1]


def test_a_missing_name_says_where_to_look(labnb):
    lab, shown = labnb
    lab.show_code("tools.py", "no_such_function")
    assert "isn't in `tools.py`" in shown[-1] and "../agent/tools.py" in shown[-1]


def test_a_missing_or_broken_file_is_explained_not_a_traceback(labnb, tmp_path, monkeypatch):
    lab, shown = labnb
    lab.show_code("no_such_file.py", "x")
    assert "There's no `no_such_file.py`" in shown[-1]
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n")
    monkeypatch.setattr(lab, "AGENT", tmp_path)
    lab.show_code("broken.py", "f")
    assert "has a Python error on line 1" in shown[-1]


def test_only_top_level_names_and_named_methods_match(labnb, tmp_path, monkeypatch):
    lab, shown = labnb
    (tmp_path / "m.py").write_text(
        "import os as summary\n\ndef outer():\n    summary = 1\n    def g():\n        pass\n\n"
        "class K:\n    def g(self):\n        return 2\n\nY = Z = 4\n")
    monkeypatch.setattr(lab, "AGENT", tmp_path)
    lab.show_code("m.py", "summary")          # an import alias and a local variable aren't shown
    assert "isn't in" in shown[-1]
    lab.show_code("m.py", "K.g")
    assert "return 2" in shown[-1]
    lab.show_code("m.py", "g")                # a nested function isn't a top-level name
    assert "isn't in" in shown[-1]
    lab.show_code("m.py", "Z")
    assert "Y = Z = 4" in shown[-1]


def test_tool_results_show_arguments_and_results_as_indented_json(labnb, tmp_path):
    lab, shown = labnb
    arguments = {"query": "coolant pump", "product": "K-400"}
    result = {"results": [{"part_number": "KI-CP-40817", "name": "Coolant pump <assembly>"}]}
    (tmp_path / "summary.json").write_text(json.dumps(
        {"tool_calls": [{"name": "find_part", "arguments": arguments, "result": result}]}))
    lab.tool_results(tmp_path)
    text = shown[-1]
    for value in (arguments, result):
        block = html.escape(json.dumps(value, indent=2, ensure_ascii=False))
        assert f">{block}</pre>" in text and "\n  " in block
    assert "<code>{" not in text and text.count("<pre") == 2
