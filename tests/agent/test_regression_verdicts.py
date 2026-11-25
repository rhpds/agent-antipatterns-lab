"""Challenge the closing module's verdicts with plausible but incorrect run records."""
import runpy

import pytest

from conftest import AGENT


@pytest.fixture
def checks(monkeypatch):
    monkeypatch.syspath_prepend(str(AGENT))
    return runpy.run_path(str(AGENT / "regression.py"))


def call(name, data=None, category="ok", **arguments):
    return {"name": name, "arguments": arguments,
            "result": {"category": category, "retryable": False, "detail": "",
                       "data": data}}


def record(*calls, offered=(), answer=""):
    return {"tool_calls": list(calls), "tools_offered": list(offered), "answer": answer,
            "ended_by": "stop", "turns": 3}


@pytest.mark.parametrize("case,summary", [
    ("check_m1", record(call("check_stock", {"results": []}))),
    ("check_m1", record(call("find_part", {"results": [{"part_number": "WRONG"}]}))),
    ("check_m3", record(call("find_part", {"results": [{"part_number": "KI-CP-40817"}]}),
                        call("check_stock", {"results": []}, category="no_results",
                             part_number="KI-XX-00000", depot="Denver"))),
    ("check_m4", record(call("check_stock", {"results": []}, part_number="KI-HS-60233", depot="Portland"),
                        call("find_part", category="bad_request"))),
    ("check_m5", record(call("search_bulletins", {"passages": [{"source": "SB-2024-102"}]}),
                        offered=["search_bulletins"], answer="Replace the temperature sensor.")),
    ("check_m5_miss", record(call("find_part", {"results": []}, category="no_results"),
                             offered=["search_bulletins"])),
])
def test_regression_rejects_evidence_that_does_not_prove_the_case(checks, case, summary):
    """Scenario: The regression run checks every earlier case against the assembled agent"""
    verdict, reason = checks[case](summary, 6)
    assert verdict == "FAIL", reason


def test_valid_tool_results_are_accepted_with_or_without_a_name_prefix(checks):
    """Scenario: The regression run checks every earlier case against the assembled agent"""
    for prefix in ("", "kestrel_"):
        part = call(prefix + "find_part", {"results": [{"part_number": "KI-CP-40817"}]})
        stock = call(prefix + "check_stock", {"results": [{"depot": "Denver", "qty": 3}]},
                     part_number="KI-CP-40817", depot="Denver")
        assert checks["check_m1"](record(part), 6)[0] == "PASS"
        assert checks["check_m3"](record(part, stock), 6)[0] == "PASS"
        assert checks["check_m5"](record(call(prefix + "search_bulletins", {"passages": [{"source": "SB-2024-102"}]}),
                                         offered=[prefix + "search_bulletins"], answer="See SB-2024-102."), 6)[0] == "PASS"
        assert checks["check_m5_miss"](record(call(prefix + "search_bulletins", {"passages": []}, category="no_results"),
                                              offered=[prefix + "search_bulletins"]), 6)[0] == "PASS"


def test_a_categorized_error_cannot_hide_a_confident_out_of_stock_answer(checks):
    """Scenario: With the error contract, a bad depot is no longer mistaken for out of stock"""
    stock = call("kestrel_check_stock", category="bad_request", depot="Portland")
    stock["result"]["detail"] = "unknown depot 'Portland'; Kestrel depots are Denver, Phoenix, Chicago"
    wrong = record(stock, answer="The sensor is not available at Portland. Try Denver instead.")
    assert checks["check_m4"](wrong, 6)[0] == "FAIL"
    corrected = record(stock, answer="I could not check stock: Portland is an unknown depot. Try Denver.")
    assert checks["check_m4"](corrected, 6)[0] == "PASS"
