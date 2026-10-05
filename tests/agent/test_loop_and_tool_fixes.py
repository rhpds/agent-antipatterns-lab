"""Modules 3-4: the supplied fixes, and the faults they fix."""
import json
import textwrap

from conftest import fixture_part, read_json

PUMP = fixture_part("circulation pump", "K-400")


def test_module3_fix_terminates_on_stop_with_results_in_messages(work):
    work.repoint_to_validated()
    work.apply_solution("module-03")
    summary, run_dir = work.agent("m3")
    assert summary["ended_by"] == "stop" and summary["turns"] == 3        # well below the cap of 6
    first, second = summary["tool_calls"]
    assert (first["name"], second["name"]) == ("find_part", "check_stock")
    assert second["arguments"]["part_number"] == PUMP                      # chain came from find_part's output
    request3 = read_json(run_dir / "03-request.json")
    tool_msgs = [m for m in request3["messages"] if m["role"] == "tool"]
    assistant = [m for m in request3["messages"] if m.get("tool_calls")]
    assert len(tool_msgs) == 2 and len(assistant) == 2
    ids = [c["id"] for m in assistant for c in m["tool_calls"]]
    assert [m["tool_call_id"] for m in tool_msgs] == ids                   # each result matches its call
    assert "in stock" in summary["answer"]


def test_module3_defect1_alone_changes_behaviour(work):
    """Appending results (defect 1 only) is enough to stop the repetition."""
    work.repoint_to_validated()
    src = (work.path / "agent.py").read_text()
    patched = src.replace(
        "                runlog.add_tool_call(call.function.name, arguments, result)\n",
        "                runlog.add_tool_call(call.function.name, arguments, result)\n"
        "                messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json.dumps(result)})\n")
    patched = patched.replace(
        "            for call in message.tool_calls:",
        "            messages.append({'role': 'assistant', 'content': message.content, 'tool_calls': [\n"
        "                {'id': c.id, 'type': 'function', 'function': {'name': c.function.name,\n"
        "                 'arguments': c.function.arguments}} for c in message.tool_calls]})\n"
        "            for call in message.tool_calls:")
    assert patched != src
    (work.path / "agent.py").write_text(patched)
    summary, _ = work.agent("m3")
    assert summary["turns"] == 3 and summary["ended_by"] == "plain_answer"


def test_module4_swallowed_failure_then_surfaced(work):
    work.repoint_to_validated()
    work.apply_solution("module-03")
    # fault: Portland (unknown depot) -> the filter is dropped, an empty 200-style envelope comes back
    before, _ = work.agent("m4")
    stock = before["tool_calls"][1]
    assert stock["name"] == "check_stock" and stock["arguments"]["depot"] == "Portland"
    assert stock["result"] == {"results": []}
    assert before["ended_by"] == "stop" and "not available" in before["answer"]   # confident, wrong
    # fix: contract
    work.apply_solution("module-04")
    after, _ = work.agent("m4")
    stock = after["tool_calls"][1]
    assert stock["result"]["category"] == "bad_request" and stock["result"]["retryable"] is False
    assert "Portland" in stock["result"]["detail"]
    assert "could not complete" in after["answer"]
    assert after["turns"] == 3


def test_module4_no_results_and_ok_are_distinguishable(work):
    work.repoint_to_validated()
    work.apply_solution("module-04")
    ok, _ = work.agent("m3")                                  # covered: pump at Denver
    assert ok["tool_calls"][1]["result"]["category"] == "ok"
    assert ok["tool_calls"][1]["result"]["data"]["results"][0]["qty"] == 3
    empty = work.run("-c", textwrap.dedent("""
        import json, tools
        print(json.dumps(tools.run_tool('check_stock', {'part_number': 'KI-HS-60233', 'depot': 'Denver'})))
        print(json.dumps(tools.run_tool('check_stock', {'part_number': 'pump', 'depot': 'Denver'})))
        print(json.dumps(tools.run_tool('check_stock', {'part_number': 'KI-CP-40817'})))
        print(json.dumps(tools.run_tool('nope', {})))
    """)).stdout.splitlines()
    cats = [json.loads(line)["category"] for line in empty]
    assert cats == ["no_results", "bad_request", "bad_request", "bad_request"]


RETRY_SCRIPT = textwrap.dedent("""
    import json, sys
    import tools
    from agent import load_config, run_agent
    calls = {"n": 0}
    kind = sys.argv[1]
    orig = tools.check_stock
    def flaky(part_number, depot):
        calls["n"] += 1
        if kind == "transient" and calls["n"] == 1:
            raise ConnectionError("backend down")
        if kind == "no_results":
            return tools.outcome("no_results", detail="none")
        return orig(part_number, depot)
    tools.TOOL_FUNCTIONS["check_stock"] = flaky
    s = run_agent("Can we get a replacement coolant pump for a K-400 to the Denver depot this week?", load_config())
    print(json.dumps({"calls": calls["n"], "result": s["tool_calls"][-1]["result"]}))
""")


def test_module4_only_upstream_unavailable_is_retried(work):
    work.repoint_to_validated()
    work.apply_solution("module-04")
    transient = json.loads(work.run("-c", RETRY_SCRIPT, "transient").stdout.splitlines()[-1])
    assert transient["calls"] == 2 and transient["result"]["category"] == "ok"       # retried once, recovered
    no_results = json.loads(work.run("-c", RETRY_SCRIPT, "no_results").stdout.splitlines()[-1])
    assert no_results["calls"] == 1 and no_results["result"]["category"] == "no_results"   # not retried


def test_regression_reports_per_case_on_each_state(work):
    start = work.run("regression.py").stdout
    assert "0 passed, 3 failed, 3 skipped" in start        # mismatched endpoint, starter code
    work.repoint_to_validated()
    work.apply_solution("module-04")
    mid = work.run("regression.py").stdout
    assert "3 passed, 0 failed, 3 skipped" in mid          # retrieval + gateway cases skip, do not block
    assert "SKIP  m5 " in mid and "PASS  m3 " in mid
    report = next((work.path / "runs").glob("regression-*.md")).read_text()
    assert "Symptom to layer" in report
