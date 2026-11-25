"""Show the raw request and response payloads of a run.

    python payloads.py                 # the latest run
    python payloads.py runs/<folder>   # a specific run
    python payloads.py --raw           # print the full JSON files, not the digest

The digest shows the three things module 1 and 2 teach you to look at:
whether tools were declared (request), and what came back in tool_calls and content
(response). tool_calls is shown as indented JSON, and content as the text the model wrote,
with its line breaks. An empty or missing value stays as it was sent: [] or null.
"""
import json
import pathlib
import sys

RUNS_DIR = pathlib.Path(__file__).parent / "runs"
UNDER = " " * 12  # lines that belong to a field start under its label


def field(label, text=None, lines=None):
    """A value on the label's own line, or a block of lines under the label."""
    if lines is None:
        return f"{label} = {text}"
    return f"{label} =\n" + "\n".join((UNDER + line).rstrip() for line in lines)


def tool_calls_field(label, calls):
    """tool_calls as indented JSON. [] and null stay as they were sent: the difference matters."""
    if not calls:
        return field(label, json.dumps(calls))
    return field(label, lines=json.dumps(calls, indent=2, ensure_ascii=False).split("\n"))


def content_field(label, content):
    """content as the model wrote it, line breaks and all. null when there's none, "" when it's empty."""
    if content is None or content == "":
        return field(label, json.dumps(content))
    return field(label, lines=str(content).split("\n"))


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
        print(tool_calls_field("          tool_calls   ", msg.get("tool_calls")))
        print(content_field("          content      ", msg.get("content")))
    print(where_to_read(run_dir))
    try:
        trace = json.loads((run_dir / "summary.json").read_text()).get("trace_url")
    except (OSError, ValueError):
        trace = None
    if trace:
        print(f"Trace in MLflow: {trace}")


def where_to_read(run_dir):
    """Name the files to open, as the JupyterLab file browser shows them (from the home
    folder), so participants can read the JSON as a tree instead of scrolling the terminal."""
    folder = run_dir.resolve()
    try:
        folder = folder.relative_to(pathlib.Path.home().resolve())
    except (ValueError, RuntimeError):  # outside home, or no home folder at all
        pass
    return (f"\nTo read the full JSON, open this folder in the file browser:\n  {folder}/\n"
            "  NN-request.json and NN-response.json: what was sent and what came back, per model call\n"
            "  summary.json: the whole run, including every tool call and what the tool returned\n"
            "Or print them here with: python payloads.py --raw")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show(pathlib.Path(args[0]) if args else latest_run(), raw="--raw" in sys.argv)
