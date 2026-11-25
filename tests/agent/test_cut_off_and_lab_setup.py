"""A cut-off regression run fails (acceptance/lab/regression-cut-off-runs.feature), and the lab's
own gateway setup isn't labelled as a participant edit (acceptance/lab/lab-setup-versions.feature)."""
import json
import runpy
import subprocess
import sys

import pytest

from conftest import AGENT
from test_agent_versions import checkout, latest_trace_version  # noqa: F401  (fixture and helper)

LAB_GATEWAY = "https://lab-gateway.example.com/mcp"


@pytest.fixture
def regression(monkeypatch):
    monkeypatch.syspath_prepend(str(AGENT))
    return runpy.run_path(str(AGENT / "regression.py"))


def passing_m1(ended_by):
    call = {"name": "find_part", "arguments": {"query": "coolant pump"},
            "result": {"category": "ok", "retryable": False, "detail": "",
                       "data": {"results": [{"part_number": "KI-CP-40817"}]}}}
    return {"tool_calls": [call], "tools_offered": ["find_part"], "answer": "",
            "ended_by": ended_by, "turns": 2}


def test_a_case_cut_off_before_its_answer_fails_and_says_to_rerun(regression):
    """Scenario: A regression case whose run was cut off doesn't pass"""
    assert regression["judge"](regression["check_m1"], passing_m1("stop"), 6)[0] == "PASS"
    status, reason = regression["judge"](regression["check_m1"], passing_m1("length"), 6)
    assert status == "FAIL"
    assert "cut off before it finished its answer" in reason
    assert "run the set again" in reason


@pytest.mark.parametrize("case", ["check_m1", "check_m3", "check_m4", "check_m5", "check_m5_miss", "check_m6"])
def test_any_cut_off_case_fails_whatever_its_check_found(regression, case):
    """Scenario: Any regression case cut off before its answer fails"""
    status, reason = regression["judge"](regression[case], passing_m1("length"), 6)
    assert status == "FAIL" and "cut off" in reason


def connect_like_module_7(dest):
    """What module 7's setup cell does: write the workbench's gateway address into config.toml."""
    config = dest / "config.toml"
    config.write_text(config.read_text().replace('gateway_url = ""', "gateway_url = " + json.dumps(LAB_GATEWAY), 1))


@pytest.fixture
def lab_checkout(checkout, endpoints):
    """The checkout, plus the version a workbench with the lab's gateway address would report."""
    dest, run, _ = checkout

    def version():
        env = {"PATH": "/usr/bin:/bin", "HOME": str(dest.parent), "LAB_GATEWAY_URL": LAB_GATEWAY,
               "LAB_MISMATCHED_URL": endpoints["mismatched"], "LAB_VALIDATED_URL": endpoints["validated"]}
        out = subprocess.run([sys.executable, "-c", "import version; print(version.current())"],
                             cwd=dest, env=env, capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, out.stderr
        return out.stdout.strip()
    return dest, run, version


def test_module_7_setup_is_not_a_participant_edit(lab_checkout):
    """Scenario: Module 7's gateway setup doesn't count as a participant edit"""
    dest, run, version = lab_checkout
    run("reset.py", "7")
    connect_like_module_7(dest)
    assert version() == "kestrel-m7-start"


def test_a_participants_own_change_is_still_modified(lab_checkout):
    """Scenario: A participant's own change to the agent is still labelled modified"""
    dest, run, version = lab_checkout
    run("reset.py", "7")
    connect_like_module_7(dest)
    (dest / "agent.py").write_text((dest / "agent.py").read_text() + "\n# my edit\n")
    assert version() == "kestrel-m7-start-modified"
    # Any other gateway address is the participant's own edit, too.
    (dest / "agent.py").write_text((dest / "agent.py").read_text().replace("\n# my edit\n", ""))
    config = dest / "config.toml"
    config.write_text(config.read_text().replace(json.dumps(LAB_GATEWAY), json.dumps("https://elsewhere.example/mcp")))
    assert version() == "kestrel-m7-start-modified"


def test_module_6_instructed_gateway_edit_is_not_a_participant_edit(lab_checkout):
    """Scenario: Following module 6's instruction to set the gateway doesn't count as a participant edit"""
    dest, run, version = lab_checkout
    run("reset.py", "6")
    config = dest / "config.toml"
    # As a participant would type it in the editor, single quotes and all.
    config.write_text(config.read_text().replace('gateway_url = ""', f"gateway_url = '{LAB_GATEWAY}'", 1))
    assert version() == "kestrel-m6-start"
    # Before module 6, the same address is an edit the lab didn't ask for.
    run("reset.py", "5")
    config.write_text(config.read_text().replace('gateway_url = ""', f"gateway_url = '{LAB_GATEWAY}'", 1))
    assert version() == "kestrel-m5-start-modified"
