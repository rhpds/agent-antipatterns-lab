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


def test_live_module6_rejects_a_gateway_chain_using_an_invented_part(monkeypatch, tmp_path):
    """Scenario: The agent reaches its tools through the lab's gateway"""
    part = tool("find_part", {"category": "ok", "data": {"results": [{"part_number": "KI-CP-40817"}]}})
    stock = tool("check_stock", {"category": "ok", "data": {"results": [{"depot": "Denver", "qty": 3}]}},
                 part_number="KI-CP-40817", depot="Denver")
    local = summary(part, stock)
    incorrect = summary(part, tool("kestrel_check_stock", {"category": "no_results", "data": {"results": []}},
                                   part_number="KI-XX-00000", depot="Denver"))
    before = summary()
    after = summary(tool("kestrel_estimate_delivery", {"category": "ok", "data": {"transit_days": 1}}))
    with pytest.raises(AssertionError):
        verify(monkeypatch, tmp_path, 6, [local, incorrect, before, after])


def test_live_module6_accepts_matching_pump_stock_with_an_additional_seal_lookup(monkeypatch, tmp_path):
    """Scenario: The agent reaches its tools through the lab's gateway"""
    part = tool("find_part", {"category": "ok", "data": {"results": [{"part_number": "KI-CP-40817"}]}})
    stock = tool("check_stock", {"category": "ok", "data": {"results": [{"depot": "Denver", "qty": 3}]}},
                 part_number="KI-CP-40817", depot="Denver")
    local = summary(part, stock)
    gateway = summary(part, stock, tool("kestrel_check_stock", {"category": "ok", "data": {"results": [{"depot": "Denver", "qty": 12}]}},
                                       part_number="KI-SK-40233", depot="Denver"))
    before = summary()
    after = summary(tool("kestrel_estimate_delivery", {"category": "ok", "data": {"transit_days": 1}}))
    assert verify(monkeypatch, tmp_path, 6, [local, gateway, before, after]) == {}
