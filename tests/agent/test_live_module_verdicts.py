"""Live module verdicts must examine the lesson, not merely successful cell execution."""
import json
import runpy

import pytest

from conftest import AGENT, REPO


def tool(name, result, **arguments):
    return {"name": name, "arguments": arguments, "result": result}


def summary(*tools, answer=""):
    return {"tool_calls": list(tools), "tools_offered": [], "answer": answer,
            "ended_by": "stop", "turns": 3, "trace_url": "https://mlflow.example/trace"}


def verify(monkeypatch, tmp_path, number, records, prompts=None):
    monkeypatch.syspath_prepend(str(AGENT))
    for i, record in enumerate(records):
        directory = tmp_path / "agent/runs" / f"run-{i:02d}"
        directory.mkdir(parents=True)
        (directory / "summary.json").write_text(json.dumps(record))
        if prompts and i < len(prompts):
            (directory / "01-request.json").write_text(json.dumps({"messages": [{"role": "system", "content": prompts[i]}]}))
    if prompts:
        (tmp_path / "agent/config.toml").write_text('[agent]\nsystem_prompt = "plain"\nsystem_prompt_strong = "strong"\n')
    checker = runpy.run_path(str(REPO / "qa-automation/workbench-check.py"))
    return checker["verify_module"](number, tmp_path)


def test_live_module2_rejects_a_stronger_prompt_that_was_never_sent(monkeypatch, tmp_path):
    """Scenario: A stronger prompt doesn't make the tools fire"""
    validated = summary(tool("find_part", {"results": [{"part_number": "KI-CP-40817"}]}))
    with pytest.raises(AssertionError):
        verify(monkeypatch, tmp_path, 2, [summary(), summary(), validated], prompts=["plain", "plain"])


def test_live_module5_rejects_a_start_that_did_not_demonstrate_the_invention(monkeypatch, tmp_path):
    """Scenario: Without knowledge search, the agent invents a cause for fault F-21"""
    start = summary(tool("find_part", {"category": "no_results"}), answer="No part found; consult support.")
    grounded = summary(tool("search_bulletins", {"category": "ok", "data": {"passages": [{"source": "SB-2024-102"}]}}),
                       answer="See SB-2024-102 for coolant loop pressure low.")
    miss = summary(tool("search_bulletins", {"category": "no_results", "data": {"passages": []}}))
    with pytest.raises(AssertionError):
        verify(monkeypatch, tmp_path, 5, [start, grounded, miss])


def test_live_module4_rejects_an_answer_that_still_calls_bad_input_out_of_stock(monkeypatch, tmp_path):
    """Scenario: Every module works through the participant instructions"""
    before = summary(tool("check_stock", {"results": []}, depot="Portland"))
    after = summary(tool("check_stock", {"category": "bad_request", "detail": "unknown depot Portland"},
                         depot="Portland"), answer="The sensor is not available at Portland.")
    with pytest.raises(AssertionError):
        verify(monkeypatch, tmp_path, 4, [before, after])


def closing_records():
    """One passing run record per regression case, in the order regression.py runs them."""
    part = tool("find_part", {"category": "ok", "data": {"results": [{"part_number": "KI-CP-40817"}]}})
    stock = tool("check_stock", {"category": "ok", "data": {"results": [{"depot": "Denver", "qty": 3}]}},
                 part_number="KI-CP-40817", depot="Denver")
    portland = tool("check_stock", {"category": "bad_request", "detail": "unknown depot 'Portland'"}, depot="Portland")
    grounded = tool("search_bulletins", {"category": "ok", "data": {"passages": [{"source": "SB-2024-102"}]}})
    miss = tool("search_bulletins", {"category": "no_results", "data": {"passages": []}})
    offered = ["find_part", "check_stock", "search_bulletins"]
    records = [summary(part), summary(part, stock),
               summary(part, portland, answer="I could not check stock: Portland is an unknown depot."),
               summary(grounded, answer="See SB-2024-102."), summary(miss)]
    for record in records:
        record["tools_offered"] = offered
    return records


def test_live_closing_module_needs_every_case_to_pass(monkeypatch, tmp_path):
    """Scenario: Every module works through the participant instructions"""
    assert verify(monkeypatch, tmp_path, 6, closing_records()) == {"regression": {"PASS": 5, "FAIL": 0, "SKIP": 0}}


def test_live_closing_module_rejects_a_cut_off_case(monkeypatch, tmp_path):
    """Scenario: A regression case whose run was cut off doesn't pass"""
    records = closing_records()
    records[1]["ended_by"] = "length"
    with pytest.raises(AssertionError):
        verify(monkeypatch, tmp_path, 6, records)
