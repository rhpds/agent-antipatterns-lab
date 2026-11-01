"""The lab's notebooks are valid and their code parses (no kernel needed)."""
import ast
import json
import pathlib

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
