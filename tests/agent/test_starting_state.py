"""Modules 1-3: the starter agent as shipped, and what repointing does to it."""
from conftest import fixture_part, read_json

PUMP = fixture_part("circulation pump", "K-400")


def test_module1_confident_answer_no_tool_calls_and_payloads_saved(work):
    summary, run_dir = work.agent("m1")
    # one model turn, plain answer, no tool invoked
    assert summary["turns"] == 1 and summary["ended_by"] == "plain_answer" and summary["tool_calls"] == []
    assert summary["answer"].strip()
    assert PUMP not in summary["answer"]               # the confident answer is invented
    # payloads saved without any debug switch
    request, response = read_json(run_dir / "01-request.json"), read_json(run_dir / "01-response.json")
    assert [t["function"]["name"] for t in request["tools"]] == ["find_part", "check_stock"]
    assert "stream" not in request                      # non-streaming (vLLM #31871)
    choice = response["choices"][0]
    assert choice["message"]["tool_calls"] == [] and choice["finish_reason"] == "stop"
    assert "<tool_call>" in choice["message"]["content"]   # the stranded hermes-format call
    assert work.endpoints["mismatched"] in summary["endpoint"]


def test_payload_viewer_shows_the_evidence(work):
    work.agent("m1")
    out = work.run("payloads.py").stdout
    assert "tools declared: ['find_part', 'check_stock']" in out
    assert "tool_calls    = []" in out and "finish_reason = stop" in out


def test_module2_stronger_prompt_changes_wording_not_tool_calls(work):
    plain, _ = work.agent("m1")
    strong, run_dir = work.agent("m1", "--strong-prompt")
    assert strong["tool_calls"] == [] and strong["answer"] != plain["answer"]
    assert read_json(run_dir / "01-response.json")["choices"][0]["message"]["tool_calls"] == []


def test_module2_repoint_populates_tool_calls_and_tool_executes(work):
    work.repoint_to_validated()                          # edit config.toml, as the lab says
    summary, run_dir = work.agent("m1")
    message = read_json(run_dir / "01-response.json")["choices"][0]["message"]
    assert message["tool_calls"] and message["tool_calls"][0]["function"]["name"] == "find_part"
    assert message["content"] is None                    # call no longer stranded in content
    first = summary["tool_calls"][0]
    assert first["name"] == "find_part"
    assert first["result"]["results"][0]["part_number"] == PUMP   # executed against fixtures


def test_module3_starter_loop_repeats_until_cap(work):
    work.repoint_to_validated()
    summary, run_dir = work.agent("m3")
    assert summary["ended_by"] == "max_turns" and summary["turns"] == 6
    calls = summary["tool_calls"]
    assert len(calls) == 6 and {c["name"] for c in calls} == {"find_part"}      # check_stock never reached
    assert len({str(c["arguments"]) for c in calls}) == 1                       # same arguments every turn
    # the harness re-sends an identical message list: no tool message ever appended
    last = read_json(run_dir / "06-request.json")
    assert [m["role"] for m in last["messages"]] == ["system", "user"]


def test_tracing_is_a_noop_without_mlflow_uri(work):
    summary, _ = work.agent("m1")                        # env has no MLFLOW_TRACKING_URI
    assert summary["turns"] == 1
