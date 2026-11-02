"""Send one identical request to both class endpoints and show the two responses side by side.

    python compare_endpoints.py           # the module 1 question
    python compare_endpoints.py --q m3    # another named test question

Both endpoints serve the same model with the same weights. This script sends each of them
the same request the agent sends (same messages, same tools, same settings) and prints
what came back in finish_reason, tool_calls and content, so the two can be compared line
by line. It doesn't save anything under runs/ and doesn't change config.toml.
"""
import argparse
import itertools
import json
import os
import shutil
import sys
import textwrap
from urllib.parse import urlparse

import openai

from agent import load_config
from questions import QUESTIONS
from reset import MISMATCHED, VALIDATED
from toolbox import open_toolbox


def build_body(config, question):
    """The request agent.py sends on its first turn (see llm.call_model)."""
    model, agent_cfg = config["model"], config["agent"]
    return {
        "model": model["name"],
        "messages": [{"role": "system", "content": agent_cfg["system_prompt"]},
                     {"role": "user", "content": question}],
        "temperature": model.get("temperature", 0),
        "seed": model.get("seed", 0),
        "max_tokens": model.get("max_tokens", 1024),
        "tools": open_toolbox(config).definitions,
        "tool_choice": "auto",
    }


def ask(base_url, body, config):
    """One non-streaming request, as llm.call_model sends it. Returns the fields to compare,
    read from the response as it came over the wire (so [] and null stay distinct)."""
    client = openai.OpenAI(
        base_url=base_url,
        api_key=os.environ.get(config["model"].get("api_key_env", "OPENAI_API_KEY"), "EMPTY"),
        timeout=config["model"].get("timeout_seconds", 120),
        max_retries=0,
    )
    try:
        raw = client.chat.completions.with_raw_response.create(**body)
        choice = json.loads(raw.http_response.text)["choices"][0]
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    message = choice.get("message") or {}
    calls = message.get("tool_calls")
    if calls:
        shown = "; ".join(f"{c['function']['name']} {c['function']['arguments']}" for c in calls)
    else:
        shown = json.dumps(calls)  # [] or null, exactly as sent
    return {
        "finish_reason": choice.get("finish_reason"),
        "tool_calls": shown,
        "content": json.dumps(message.get("content"), ensure_ascii=False),
    }


def label(base_url):
    """The endpoint's service name, for example qwen3-8b-a."""
    return (urlparse(base_url).hostname or base_url).split(".")[0].removesuffix("-predictor")


def blocks(result, width):
    """One endpoint's fields (or its error), each wrapped to the column width."""
    fields = ["error"] if "error" in result else ["finish_reason", "tool_calls", "content"]
    return [textwrap.wrap(f"{field}: {result[field]}", width) or [f"{field}:"] for field in fields]


def side_by_side(left, right, names, width):
    """Each endpoint rendered on its own, so one failing never hides the other's response.
    Fields start on the same row on both sides, however far either one wraps."""
    rows = [f"{names[0]:<{width}}   {names[1]}", f"{'-' * len(names[0]):<{width}}   {'-' * len(names[1])}"]
    for a, b in itertools.zip_longest(blocks(left, width), blocks(right, width), fillvalue=[]):
        for x, y in itertools.zip_longest(a, b, fillvalue=""):
            rows.append(f"{x:<{width}}   {y}".rstrip())
        rows.append("")
    return "\n".join(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--q", choices=sorted(QUESTIONS), default="m1", help="a named test question (default m1)")
    args = ap.parse_args(argv)

    config = load_config()
    try:
        body = build_body(config, QUESTIONS[args.q])
    except Exception as exc:  # for example, module 6's gateway is unreachable
        sys.exit(f"compare_endpoints: couldn't load the agent's tools: {exc}")
    print(f"Question: {QUESTIONS[args.q]}")
    print(f"Sent the same request to both endpoints (model {body['model']}).\n")
    left, right = ask(MISMATCHED, body, config), ask(VALIDATED, body, config)
    width = max(30, (shutil.get_terminal_size((100, 24)).columns - 3) // 2)
    print(side_by_side(left, right, (label(MISMATCHED), label(VALIDATED)), width))


if __name__ == "__main__":
    main()
