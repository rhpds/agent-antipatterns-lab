"""A cut-off regression run fails (acceptance/lab/regression-cut-off-runs.feature)."""
import runpy

import pytest

from conftest import AGENT


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


def test_the_regression_set_reports_a_cut_off_case_as_failed(regression, tmp_path, capsys):
    """Scenario: A regression case whose run was cut off doesn't pass"""
    main = regression["main"]
    # Every case's run is cut off; the report must say so, case by case.
    main.__globals__["run_agent"] = lambda question, config: passing_m1("length")
    main.__globals__["RUNS_DIR"] = tmp_path
    main([])
    out = capsys.readouterr().out
    assert "0 passed, 5 failed, 0 skipped" in out
    report = next(tmp_path.glob("regression-*.md")).read_text()
    assert report.count("| FAIL | the run was cut off before it finished its answer") == 5
    assert "run the set again" in report


@pytest.mark.parametrize("case", ["check_m1", "check_m3", "check_m4", "check_m5", "check_m5_miss"])
def test_any_cut_off_case_fails_whatever_its_check_found(regression, case):
    """Scenario: Any regression case cut off before its answer fails"""
    status, reason = regression["judge"](regression[case], passing_m1("length"), 6)
    assert status == "FAIL" and "cut off" in reason
