"""Every approved acceptance scenario is named in the docstring of a test.

The scenarios under acceptance/ are locked and approved by David. This keeps each one
tied to a test: a scenario whose exact title appears in no test docstring fails here,
so an unbound scenario can't slip in. To bind one, put its exact title in the docstring of
the test that checks it, on a line of its own:

    def test_something():
        \"\"\"Scenario: <exact title from the .feature file>\"\"\"
"""
import ast
import pathlib
import re

from conftest import REPO

SCENARIO = re.compile(r"^\s*Scenario(?: Outline)?:\s*(.+?)\s*$", re.MULTILINE)


def scenario_titles(feature_dir):
    """{title: feature file} for every scenario under feature_dir."""
    titles = {}
    for feature in sorted(pathlib.Path(feature_dir).rglob("*.feature")):
        for title in SCENARIO.findall(feature.read_text()):
            titles[title] = feature
    return titles


def named_scenarios(tests_dir):
    """Every "Scenario: <title>" line found in a test function's docstring under tests_dir."""
    named = set()
    for path in sorted(pathlib.Path(tests_dir).rglob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                for line in (ast.get_docstring(node) or "").splitlines():
                    if line.strip().startswith("Scenario:"):
                        named.add(" ".join(line.split()))
    return named


def unbound(feature_dir, tests_dir):
    named = named_scenarios(tests_dir)
    return [f"{feature.name}: {title}" for title, feature in scenario_titles(feature_dir).items()
            if f"Scenario: {title}" not in named]


def test_every_scenario_is_named_in_a_test_docstring():
    """The check that keeps acceptance/ and the tests in step."""
    missing = unbound(REPO / "acceptance", REPO / "tests")
    assert not missing, "scenarios no test names in its docstring:\n  " + "\n  ".join(missing)


def test_the_guard_catches_an_unbound_scenario(tmp_path):
    """The check itself works: it flags a scenario no test names (or only a longer title) and accepts one that is named."""
    (tmp_path / "x.feature").write_text("Feature: f\n\n  Scenario: Bound one\n    Given a\n\n  Scenario: Loose one\n\n  Scenario: Bound\n")
    (tmp_path / "test_x.py").write_text('def test_a():\n    """Scenario: Bound one"""\n\ndef helper():\n    """Scenario: Loose one"""\n')
    assert unbound(tmp_path, tmp_path) == ["x.feature: Loose one", "x.feature: Bound"]
