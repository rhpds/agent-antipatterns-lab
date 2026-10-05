"""Show the raw request and response payloads of a run.

    python payloads.py                 # the latest run
    python payloads.py runs/<folder>   # a specific run
    python payloads.py --raw           # print the full JSON files, not the digest

The digest shows the three things module 1 and 2 teach you to look at:
whether tools were declared (request), and what came back in tool_calls and content
(response).
"""
import json
import pathlib
import sys

RUNS_DIR = pathlib.Path(__file__).parent / "runs"


def latest_run():
    runs = sorted(p for p in RUNS_DIR.glob("*") if p.is_dir())
    if not runs:
        sys.exit("no runs yet: run  python agent.py --q m1  first")
    return runs[-1]


def show(run_dir, raw=False):
    print(f"Run: {run_dir}")
    for req_path in sorted(run_dir.glob("*-request.json")):
        n = req_path.name.split("-")[0]
        resp_path = run_dir / f"{n}-response.json"
        if raw:
            print(f"\n=== {req_path.name} ===\n{req_path.read_text()}")
            print(f"\n=== {resp_path.name} ===\n{resp_path.read_text() if resp_path.exists() else '(none)'}")
            continue
        req = json.loads(req_path.read_text())
        print(f"\n--- model call {n} ---")
        print(f"request:  {len(req['messages'])} messages, tools declared: "
              f"{[t['function']['name'] for t in req.get('tools', [])]}")
        if not resp_path.exists():
            print("response: (none)")
            continue
        try:
            resp = json.loads(resp_path.read_text())
            choice = resp["choices"][0]
        except (ValueError, KeyError):
            print(f"response: not a completion:\n{resp_path.read_text()}")
            continue
        msg = choice["message"]
        print(f"response: finish_reason = {choice.get('finish_reason')}")
        print(f"          tool_calls    = {json.dumps(msg.get('tool_calls'))}")
        print(f"          content       = {json.dumps(msg.get('content'))}")
    print(f"\nFull JSON files are in {run_dir}  (use --raw to print them)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show(pathlib.Path(args[0]) if args else latest_run(), raw="--raw" in sys.argv)
