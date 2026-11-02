"""Per-run record: the raw request and response for every model call.

Every run writes a folder under runs/ so you never have to turn on debug logging:

    runs/<timestamp>/
        01-request.json    exactly what the agent sent to the endpoint
        01-response.json   exactly what came back (the raw HTTP body)
        02-request.json    ... one pair per model call
        summary.json       turns, tool calls, how the run ended

View them with:  python payloads.py            (latest run)
                 python payloads.py runs/<dir> (a specific run)
"""
import datetime
import json
import pathlib

RUNS_DIR = pathlib.Path(__file__).parent / "runs"


class RunLog:
    def __init__(self, question, endpoint, runs_dir=None):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.dir = pathlib.Path(runs_dir or RUNS_DIR) / stamp
        self.dir.mkdir(parents=True, exist_ok=True)
        self.question = question
        self.endpoint = endpoint
        self.model_calls = []   # one entry per model call
        self.tool_calls = []    # one entry per tool invocation
        self.outcome = None
        self.tools_offered = []

    def save_request(self, n, body):
        (self.dir / f"{n:02d}-request.json").write_text(json.dumps(body, indent=2))

    def save_response(self, n, raw_text, status=200):
        try:
            text = json.dumps(json.loads(raw_text), indent=2)
        except ValueError:
            text = raw_text
        (self.dir / f"{n:02d}-response.json").write_text(text)

    def add_model_call(self, n, finish_reason, tool_call_count):
        self.model_calls.append(
            {"call": n, "finish_reason": finish_reason, "tool_calls": tool_call_count}
        )

    def add_tool_call(self, name, arguments, result):
        self.tool_calls.append({"name": name, "arguments": arguments, "result": result})

    def finish(self, answer, ended_by):
        self.outcome = {"answer": answer, "ended_by": ended_by}
        summary = {
            "run_dir": str(self.dir),
            "question": self.question,
            "endpoint": self.endpoint,
            "turns": len(self.model_calls),
            "ended_by": ended_by,
            "tools_offered": self.tools_offered,
            "model_calls": self.model_calls,
            "tool_calls": self.tool_calls,
            "answer": answer,
        }
        (self.dir / "summary.json").write_text(json.dumps(summary, indent=2))
        return summary
