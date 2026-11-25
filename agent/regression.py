"""Module 7: re-run every earlier failure case and report per case.

    python regression.py                    # run the whole set against the agent as it is now
    python regression.py --name my-baseline # also record it in MLflow as a named evaluation run

Each case is judged from the run record (tool calls, stop reason, error categories),
using fixed checks, including source-citation and failed-check markers in the answer; no LLM judges the result. With tracing on, the run is also recorded in MLflow as
an evaluation: one row per case, with its trace and the same PASS, FAIL or SKIP and reason,
so a later run can be compared with this one. A case that cannot apply yet (for example the
retrieval cases before module 5) is reported SKIP; nothing blocks the rest.
Writes runs/regression-<time>.md, including the symptom-to-layer checklist.
"""
import argparse
import datetime
import os
import pathlib
import sys

import tracing
from agent import load_config, run_agent
from questions import QUESTIONS
from runlog import RUNS_DIR


def offered(summary, tool):
    return any(n.endswith(tool) for n in summary["tools_offered"])


def called(summary, tool):
    return [t for t in summary["tool_calls"] if t["name"].endswith(tool)]


def categories(summary):
    return [t["result"].get("category") for t in summary["tool_calls"]]


def successful_data(call):
    """Read both the early module envelope and the module 4 error contract."""
    result = call["result"]
    if result.get("category") not in (None, "ok"):
        return {}
    return result.get("data") or result


# Each check returns (status, reason). Status is PASS, FAIL or SKIP.

def check_m1(s, cap):
    parts = {p.get("part_number") for t in called(s, "find_part")
             for p in successful_data(t).get("results", [])}
    if "KI-CP-40817" not in parts:
        return "FAIL", "find_part did not return the K-400 pump KI-CP-40817 (module 2)"
    return "PASS", "find_part returned the K-400 pump KI-CP-40817"


def check_m3(s, cap):
    names = [t["name"] for t in s["tool_calls"]]
    if s["ended_by"] == "max_turns":
        return "FAIL", f"hit the iteration cap ({cap} turns); loop did not use tool results (module 3)"
    if s["ended_by"] != "stop":
        return "FAIL", f"ended by {s['ended_by']!r}, not the model's stop condition"
    found = set()
    checked = set()
    for tool in s["tool_calls"]:
        if tool["name"].endswith("find_part"):
            found.update(p.get("part_number") for p in successful_data(tool).get("results", []))
        elif tool["name"].endswith("check_stock"):
            part = tool["arguments"].get("part_number")
            if part in found and tool["arguments"].get("depot") == "Denver" and any(
                    r.get("depot") == "Denver" and r.get("qty", 0) > 0
                    for r in successful_data(tool).get("results", [])):
                checked.add(part)
    if "KI-CP-40817" not in checked:
        return "FAIL", f"expected the looked-up K-400 pump's positive Denver stock, saw {names}"
    return "PASS", f"{s['turns']} turns (cap {cap}), ended on stop, tools {names}"


def check_m4(s, cap):
    cats = categories(s)
    if not called(s, "check_stock"):
        return "FAIL", "check_stock was never called"
    if any(t["result"].get("category") == "bad_request" and
           t["arguments"].get("depot") == "Portland" and
           "Portland" in t["result"].get("detail", "")
           for t in called(s, "check_stock")):
        answer = s["answer"].lower()
        if not any(marker in answer for marker in (
                "unknown", "invalid", "not a depot", "not a valid", "not recognized", "not recognised",
                "could not", "couldn't", "cannot", "can't", "unable", "does not exist", "doesn't exist")):
            return "FAIL", "bad_request was recorded but the answer did not explain that stock could not be checked"
        return "PASS", f"failure surfaced with a category: {cats}"
    return "FAIL", f"unknown depot returned no error category (saw {cats}): swallowed failure (module 4)"


def check_m5(s, cap):
    if not offered(s, "search_bulletins"):
        return "SKIP", "search_bulletins is not registered (module 5)"
    hits = [t for t in called(s, "search_bulletins") if t["result"].get("category") == "ok"]
    sources = {p["source"] for t in hits for p in t["result"]["data"]["passages"]}
    if "SB-2024-102" not in sources:
        return "FAIL", f"no passage from SB-2024-102 retrieved (saw {sorted(sources)})"
    if "SB-2024-102" not in s["answer"]:
        return "FAIL", "SB-2024-102 was retrieved but the answer omitted its source citation"
    return "PASS", f"answer cites retrieved bulletin SB-2024-102 (sources {sorted(sources)})"


def check_m5_miss(s, cap):
    if not offered(s, "search_bulletins"):
        return "SKIP", "search_bulletins is not registered (module 5)"
    if any(t["result"].get("category") == "no_results" and
           (t["result"].get("data") or {}).get("passages") == []
           for t in called(s, "search_bulletins")):
        return "PASS", "retrieval returned no_results (an explicit gap)"
    return "FAIL", f"expected no_results, saw {categories(s)}"


def check_m6(s, cap):
    if not offered(s, "estimate_delivery"):
        return "SKIP", "estimate_delivery is not in the tool catalog (module 6)"
    if any(successful_data(t).get("transit_days") == 1 and
           successful_data(t).get("origin_depot") == "Denver" and
           successful_data(t).get("destination") == "Boulder"
           for t in called(s, "estimate_delivery")):
        return "PASS", "estimate_delivery returned one day from Denver to Boulder"
    return "FAIL", "estimate_delivery did not return a successful one-day Denver-to-Boulder result"


def judge(check, summary, cap):
    """A case's verdict. A run the model cut off (it ran out of room before finishing its
    answer) never passes, whatever its check found."""
    status, reason = check(summary, cap)
    if summary.get("ended_by") == "length":
        return "FAIL", ("the run was cut off before it finished its answer (the model ran out of "
                        "room); run the set again")
    return status, reason


CASES = [
    ("m1", "Module 1-2: tool call fires", check_m1),
    ("m3", "Module 3: loop terminates on stop", check_m3),
    ("m4", "Module 4: swallowed failure surfaces", check_m4),
    ("m5", "Module 5: answer grounded in a bulletin", check_m5),
    ("m5-miss", "Module 5: out-of-corpus is an explicit gap", check_m5_miss),
    ("m6", "Module 6: runtime-discovered tool", check_m6),
]

CHECKLIST = """\
## Symptom to layer

| A customer says... | Look first at | Layer |
|---|---|---|
| The agent ignores its tools | How the model is served (tool-call parser), not the prompt | Model interface (module 2) |
| It loops, or runs are expensive | Whether the loop appends tool results and reads the stop condition | Agent loop (module 3) |
| It confidently reports work it did not do | Whether tool returns can express failure | Tool returns (module 4) |
| It makes things up about their own data | Whether anything grounds it in a source | Knowledge search (module 5) |
| Who can see what? | Whether tool access goes through a governed path | Platform tool access (module 6) |

Covered by discussion, not by this regression set: model and prompt regressions when a
model version changes underneath a working agent, and cost behaviour under real concurrency.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="baseline", help="run name to record in MLflow")
    ap.add_argument("--config")
    args = ap.parse_args(argv)
    tracing.init()
    config = load_config(args.config)
    cap = config["agent"]["max_turns"]

    rows, traced = [], []
    for key, title, check in CASES:
        trace_id = None
        tracing.forget_last_trace()
        try:
            summary = run_agent(QUESTIONS[key], config)
            trace_id = tracing.last_trace_id()
            # Persist the same trace link as an ordinary CLI run, so the notebook's
            # evidence table can open each regression case's actual trace.
            tracing.report(summary)
            status, reason = judge(check, summary, cap)
        except Exception as exc:  # a broken case must not stop the others
            status, reason = "FAIL", f"run raised {type(exc).__name__}: {exc}"
        rows.append((key, title, status, reason))
        if trace_id:
            traced.append((trace_id, status, f"{key}: {reason}"))
        print(f"{status:5} {key:8} {title}\n      {reason}")

    counts = {s: sum(1 for r in rows if r[2] == s) for s in ("PASS", "FAIL", "SKIP")}
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS_DIR.mkdir(exist_ok=True)
    report = RUNS_DIR / f"regression-{stamp}.md"
    lines = [f"# Regression run {stamp}", "", f"Endpoint: {config['model']['base_url']}", "",
             "| Case | Check | Result | Evidence |", "|---|---|---|---|"]
    lines += [f"| {k} | {t} | {s} | {r} |" for k, t, s, r in rows]
    report.write_text("\n".join(lines) + "\n\n" + CHECKLIST)
    print(f"Report and checklist: {report}")

    run_id = tracing.log_evaluation(args.name, {"endpoint": config["model"]["base_url"]}, traced,
                                    {"passed": counts["PASS"], "failed": counts["FAIL"], "skipped": counts["SKIP"]})
    if run_id:
        print(f"Recorded MLflow run {args.name!r} ({run_id})")
        url = tracing.evaluation_url(run_id)
        if url:
            print(f"Evaluation in MLflow: {url}")
    elif os.environ.get("MLFLOW_TRACKING_URI"):
        why = " (it couldn't be reached)" if not tracing.enabled() else ""
        print(f"The evaluation wasn't recorded in MLflow{why}. Every case is in the report above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
