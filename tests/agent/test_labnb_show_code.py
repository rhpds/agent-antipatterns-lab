"""The notebooks' lab.show_code() shows a function from agent/ with its line numbers."""
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
    assert "```python" in text and "lines" in text


def test_shows_a_top_level_name(labnb):
    lab, shown = labnb
    lab.show_code("tools.py", "TOOL_FUNCTIONS")
    assert "TOOL_FUNCTIONS = {" in shown[-1]


def test_a_missing_name_says_where_to_look(labnb):
    lab, shown = labnb
    lab.show_code("tools.py", "no_such_function")
    assert "isn't in `tools.py`" in shown[-1] and "../agent/tools.py" in shown[-1]
