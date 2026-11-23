"""The lab's notebooks are valid and their code parses (no kernel needed)."""
import ast
import json
import pathlib
from types import SimpleNamespace

import pytest

NOTEBOOKS = sorted((pathlib.Path(__file__).resolve().parents[2] / "notebooks").glob("*.ipynb"))


def test_there_is_a_notebook():
    assert NOTEBOOKS


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_is_valid_and_its_code_parses(path):
    nb = json.loads(path.read_text())
    assert nb["nbformat"] == 4
    for cell in nb["cells"]:
        assert cell.get("id")
        if cell["cell_type"] != "code":
            continue
        assert cell["outputs"] == [] and cell["execution_count"] is None   # shipped clean
        # IPython magics and shell escapes aren't Python; leave them out.
        source = "".join(line for line in cell["source"] if not line.lstrip().startswith(("%", "!")))
        ast.parse(source)


@pytest.mark.parametrize("url", ["https://lab-gateway.example/mcp", None])
def test_module7_reconnects_the_gateway_after_its_reset(tmp_path, monkeypatch, url):
    notebook = next(p for p in NOTEBOOKS if p.name.startswith("module-07-"))
    cells = json.loads(notebook.read_text())["cells"]
    connect = next((c for c in cells if c["id"] == "module-07-connect-gateway"), None)
    assert connect is not None, "Module 7 needs to restore its gateway connection after reset"
    assert cells.index(connect) > next(i for i, c in enumerate(cells) if "reset.py 7" in "".join(c["source"]))
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config.toml"
    config.write_text('[tools]\ngateway_url = ""\n')
    listed = []
    scope = {"lab": SimpleNamespace(gateway_url=lambda: url, tool_list=lambda: listed.append(True))}
    code = "".join(connect["source"])
    if url:
        exec(code, scope)
        import tomllib
        assert tomllib.loads(config.read_text())["tools"]["gateway_url"] == url
        assert listed
    else:
        with pytest.raises(RuntimeError, match="gateway"):
            exec(code, scope)
        assert config.read_text() == '[tools]\ngateway_url = ""\n'
