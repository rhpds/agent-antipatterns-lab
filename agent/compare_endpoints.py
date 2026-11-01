"""Send one identical request to both class endpoints and show the two responses side by side.

    python compare_endpoints.py           # the module 1 question
    python compare_endpoints.py --q m3    # another named test question

Both endpoints serve the same model with the same weights. This script sends each of them
the same request the agent sends (same messages, same tools, same settings) and prints
what came back in finish_reason, tool_calls and content, so the two can be compared line
by line. It doesn't save anything under runs/ and doesn't change config.toml.
"""
import argparse
import json
import os
import shutil
import textwrap
from urllib.parse import urlparse

import openai

from agent import load_config
from questions import QUESTIONS
from reset import MISMATCHED, VALIDATED
from toolbox import open_toolbox


def ask(base_url, body, config):
    """One non-streaming request, as llm.call_model sends it. Returns the fields to compare."""
    client = openai.OpenAI(
        base_url=base_url,
        api_key=os.environ.get(config["model"].get("api_key_env", "OPENAI_API_KEY"), "EMPTY"),
        timeout=config["model"].get("timeout_seconds", 120),
        max_retries=0,
    )
    try:
        choice = client.chat.completions.create(**body).choices[0]
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    calls = [f"{c.function.name} {c.function.arguments}" for c in (choice.message.tool_calls or [])]
    return {
        "finish_reason": choice.finish_reason,
        "tool_calls": "; ".join(calls) if calls else "null",
        "content": json.dumps(choice.message.content),
    }


def label(base_url):
    """The endpoint's service name, for example qwen3-8b-a."""
    return (urlparse(base_url).hostname or base_url).split(".")[0].removesuffix("-predictor")


def side_by_side(left, right, names, width):
    rows = [f"{names[0]:<{width}}   {names[1]}", f"{'-' * len(names[0]):<{width}}   {'-' * len(names[1])}"]
    fields = ["error"] if "error" in left or "error" in right else ["finish_reason", "tool_calls", "content"]
    for field in fields:
        a = textwrap.wrap(f"{field}: {left.get(field, '')}", width) or [""]
        b = textwrap.wrap(f"{field}: {right.get(field, '')}", width) or [""]
        for i in range(max(len(a), len(b))):
            rows.append(f"{(a[i] if i < len(a) else ''):<{width}}   {b[i] if i < len(b) else ''}")
        rows.append("")
    return "\n".join(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--q", choices=sorted(QUESTIONS), default="m1", help="a named test question (default m1)")
    args = ap.parse_args(argv)

    config = load_config()
    model, agent_cfg = config["model"], config["agent"]
    body = {
        "model": model["name"],
        "messages": [{"role": "system", "content": agent_cfg["system_prompt"]},
                     {"role": "user", "content": QUESTIONS[args.q]}],
        "temperature": model.get("temperature", 0),
        "seed": model.get("seed", 0),
        "max_tokens": model.get("max_tokens", 1024),
        "tools": open_toolbox(config).definitions,
        "tool_choice": "auto",
    }
    print(f"Question: {QUESTIONS[args.q]}")
    print(f"Sent the same request to both endpoints (model {model['name']}).\n")
    left, right = ask(MISMATCHED, body, config), ask(VALIDATED, body, config)
    width = max(30, (shutil.get_terminal_size((100, 24)).columns - 3) // 2)
    print(side_by_side(left, right, (label(MISMATCHED), label(VALIDATED)), width))


if __name__ == "__main__":
    main()
