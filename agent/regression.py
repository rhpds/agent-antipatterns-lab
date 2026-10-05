"""Module 7: re-run every earlier failure case and report per case.

    python regression.py                    # run the whole set against the agent as it is now
    python regression.py --name my-baseline # also record a named run in MLflow (if configured)

Each case is judged from the run record (tool calls, stop reason, error categories),
not from the wording of the answer. A case that cannot apply yet (for example the
retrieval cases before module 5) is reported SKIP; nothing blocks the rest.
Writes runs/regression-<time>.md, including the symptom-to-layer checklist.
"""
import argparse
import datetime
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


# Each check returns (status, reason). Status is PASS, FAIL or SKIP.

def check_m1(s, cap):
    if not s["tool_calls"]:
        return "FAIL", "no tool_calls: the model's tool call never fired (module 2)"
    return "PASS", f"tool called: {[t['name'] for t in s['tool_calls']]}"


def check_m3(s, cap):
    names = [t["name"] for t in s["tool_calls"]]
    if s["ended_by"] == "max_turns":
        return "FAIL", f"hit the iteration cap ({cap} turns); loop did not use tool results (module 3)"
    if s["ended_by"] != "stop":
        return "FAIL", f"ended by {s['ended_by']!r}, not the model's stop condition"
    if not (called(s, "find_part") and called(s, "check_stock")):
        return "FAIL", f"expected find_part then check_stock, saw {names}"
    return "PASS", f"{s['turns']} turns (cap {cap}), ended on stop, tools {names}"


def check_m4(s, cap):
    cats = categories(s)
    if not called(s, "check_stock"):
        return "FAIL", "check_stock was never called"
    if "bad_request" in cats:
        return "PASS", f"failure surfaced with a category: {cats}"
    return "FAIL", f"unknown depot returned no error category (saw {cats}): swallowed failure (module 4)"


def check_m5(s, cap):
    if not offered(s, "search_bulletins"):
        return "SKIP", "search_bulletins is not registered (module 5)"
    hits = [t for t in called(s, "search_bulletins") if t["result"].get("category") == "ok"]
    sources = {p["source"] for t in hits for p in t["result"]["data"]["passages"]}
    if "SB-2024-117" in sources:
        return "PASS", f"retrieval returned passages from {sorted(sources)}"
    return "FAIL", f"no passage from SB-2024-117 retrieved (saw {sorted(sources)})"


def check_m5_miss(s, cap):
    if not offered(s, "search_bulletins"):
        return "SKIP", "search_bulletins is not registered (module 5)"
    if "no_results" in categories(s):
        return "PASS", "retrieval returned no_results (an explicit gap)"
    return "FAIL", f"expected no_results, saw {categories(s)}"


def check_m6(s, cap):
    if not offered(s, "estimate_delivery"):
        return "SKIP", "estimate_delivery is not in the tool catalog (module 6)"
    if called(s, "estimate_delivery"):
        return "PASS", "estimate_delivery was discovered and used"
    return "FAIL", "estimate_delivery was available but not called"


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

    rows = []
    for key, title, check in CASES:
        try:
            summary = run_agent(QUESTIONS[key], config)
            status, reason = check(summary, cap)
        except Exception as exc:  # a broken case must not stop the others
            status, reason = "FAIL", f"run raised {type(exc).__name__}: {exc}"
        rows.append((key, title, status, reason))
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

    run_id = tracing.log_baseline(args.name, {"endpoint": config["model"]["base_url"]},
                                  {"passed": counts["PASS"], "failed": counts["FAIL"], "skipped": counts["SKIP"]})
    if run_id:
        print(f"Recorded MLflow run {args.name!r} ({run_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
