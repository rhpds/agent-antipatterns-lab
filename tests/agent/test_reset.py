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


def test_back_to_back_resets_keep_the_participants_edit(checkout):
    # Two resets in the same second (the clock is frozen so they always collide): each must
    # get its own backup directory, or the second overwrites the first's copy of the edit.
    (checkout / "agent.py").write_text("# my edit\n")
    frozen = ("import datetime, reset\n"
              "class Frozen(datetime.datetime):\n"
              "    @classmethod\n"
              "    def now(cls, tz=None): return cls(2026, 10, 14, 12, 0, 0)\n"
              "reset.datetime.datetime = Frozen\n"
              "reset.reset(5)\n"
              "open('tools.py', 'a').write('# another edit\\n')\n"
              "reset.reset(4)\n")
    subprocess.run([sys.executable, "-c", frozen], cwd=checkout, check=True, capture_output=True)
    backups = sorted((checkout / ".reset-backup").iterdir())
    assert len(backups) == 2
    assert "# my edit\n" in {p.read_text() for p in (checkout / ".reset-backup").glob("*/agent.py")}


def test_staged_new_file_is_backed_up_and_kept(checkout):
    (checkout / "mine.py").write_text("print('mine')\n")
    subprocess.run(["git", "add", "mine.py"], cwd=checkout, check=True)
    (checkout / "agent.py").write_text("# my edit\n")
    out = reset(checkout, 4)
    assert "Ready to start module 4." in out
    assert (checkout / "mine.py").read_text() == "print('mine')\n"
    assert {p.name for p in (checkout / ".reset-backup").glob("*/*.py")} == {"agent.py", "mine.py"}
    assert same(checkout, "agent.py", AGENT / "solutions" / "module-03" / "agent.py")


def test_reset_is_safe_to_repeat(checkout):
    reset(checkout, 6)
    first = {p.name: p.read_text() for p in checkout.glob("*.py")}
    reset(checkout, 6)
    assert {p.name: p.read_text() for p in checkout.glob("*.py")} == first
    assert same(checkout, "agent.py", AGENT / "solutions" / "module-05" / "agent.py")


def test_lab_supplied_copies_are_not_backed_up(checkout):
    # After a reset to module 5, agent.py, tools.py and config.toml all differ from HEAD,
    # but only by what the lab put there. A second reset must not back them up again.
    reset(checkout, 5)
    out = reset(checkout, 4)
    assert not (checkout / ".reset-backup").exists()
    assert "Your previous versions" not in out
    # An edit on top of a supplied file is the participant's own, so it is backed up.
    (checkout / "tools.py").write_text((checkout / "tools.py").read_text() + "# my tweak\n")
    out = reset(checkout, 4)
    assert "Your previous versions of tools.py are in" in out
    backups = list((checkout / ".reset-backup").glob("*/*"))
    assert [p.name for p in backups] == ["tools.py"] and "# my tweak" in backups[0].read_text()
