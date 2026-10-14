"""reset.py puts a participant's checkout in the state a module starts from."""
import shutil
import subprocess
import sys

import pytest

from conftest import AGENT, START_URL

VALIDATED_URL = "http://qwen3-8b-b-predictor.llm-serving.svc:8080/v1"


@pytest.fixture
def checkout(tmp_path):
    """A git checkout of agent/, as the workbench clone has, with the solutions."""
    dest = tmp_path / "agent"
    shutil.copytree(AGENT, dest, ignore=shutil.ignore_patterns("runs", "__pycache__", ".reset-backup"))
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "starter"]):
        subprocess.run([*git, *args], cwd=dest, check=True, capture_output=True)
    return dest


def reset(checkout, module):
    out = subprocess.run([sys.executable, "reset.py", str(module)], cwd=checkout,
                         capture_output=True, text=True, check=True)
    return out.stdout


def same(checkout, name, source):
    return (checkout / name).read_text() == source.read_text()


def test_reset_builds_each_module_start_and_backs_up_edits(checkout):
    (checkout / "agent.py").write_text("# my broken edit\n")
    config = checkout / "config.toml"
    config.write_text(config.read_text() + "\n# my note\n")

    out = reset(checkout, 5)
    assert "Ready to start module 5." in out
    assert same(checkout, "agent.py", AGENT / "solutions" / "module-04" / "agent.py")
    assert same(checkout, "tools.py", AGENT / "solutions" / "module-04" / "tools.py")
    assert VALIDATED_URL in config.read_text() and START_URL not in config.read_text()
    assert "# my note" not in config.read_text()
    backups = list((checkout / ".reset-backup").glob("*/agent.py"))
    assert len(backups) == 1 and backups[0].read_text() == "# my broken edit\n"

    reset(checkout, 4)
    assert same(checkout, "agent.py", AGENT / "solutions" / "module-03" / "agent.py")
    assert same(checkout, "tools.py", AGENT / "tools.py")

    out = reset(checkout, 1)
    assert "starter code, unchanged" in out
    assert same(checkout, "agent.py", AGENT / "agent.py") and same(checkout, "config.toml", AGENT / "config.toml")


def test_reset_is_safe_to_repeat(checkout):
    reset(checkout, 6)
    first = {p.name: p.read_text() for p in checkout.glob("*.py")}
    reset(checkout, 6)
    assert {p.name: p.read_text() for p in checkout.glob("*.py")} == first
    assert same(checkout, "agent.py", AGENT / "solutions" / "module-05" / "agent.py")
