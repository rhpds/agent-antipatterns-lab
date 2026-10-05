"""Kestrel field service parts agent.

    python agent.py --q m1                       # run a named test question
    python agent.py "your own question"
    python agent.py --q m1 --strong-prompt       # use the stronger system prompt

Three files matter: tools.py (tool definitions), this file (the loop), and
config.toml (which model endpoint to call). Every run saves the raw request and
response of each model call under runs/; see payloads.py.
"""
import argparse
import json
import pathlib
import sys
import tomllib

import tracing
from llm import call_model
from questions import QUESTIONS
from runlog import RunLog
from toolbox import open_toolbox

DEFAULT_CONFIG = pathlib.Path(__file__).parent / "config.toml"


def load_config(path=None):
    with open(path or DEFAULT_CONFIG, "rb") as f:
        return tomllib.load(f)


def run_agent(question, config, strong_prompt=False, runs_dir=None):
    """Run the agent on one question. Returns the run summary (also saved as summary.json)."""
    agent_cfg = config["agent"]
    system = agent_cfg["system_prompt_strong" if strong_prompt else "system_prompt"]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    runlog = RunLog(question, config["model"]["base_url"], runs_dir)
    toolbox = open_toolbox(config)
    runlog.tools_offered = [d["function"]["name"] for d in toolbox.definitions]

    with tracing.span("agent_run", "AGENT", inputs={"question": question}) as root:
        for turn in range(1, agent_cfg["max_turns"] + 1):
            with tracing.span(f"model_call_{turn}", "CHAT_MODEL", inputs={"messages": len(messages)}) as llm_span:
                response = call_model(config, messages, toolbox.definitions, runlog, turn)
                message = response.choices[0].message
                llm_span.set_attributes({
                    "finish_reason": response.choices[0].finish_reason,
                    "tool_call_count": len(message.tool_calls or []),
                })

            if not message.tool_calls:
                # The model answered in plain text.
                summary = runlog.finish(message.content, "plain_answer")
                root.set_outputs({"answer": message.content})
                return summary

            for call in message.tool_calls:
                arguments = json.loads(call.function.arguments)
                with tracing.span(call.function.name, "TOOL", inputs=arguments) as tool_span:
                    result = toolbox.call(call.function.name, arguments)
                    tool_span.set_outputs(result)
                runlog.add_tool_call(call.function.name, arguments, result)

            if "final answer" in (message.content or "").lower():
                summary = runlog.finish(message.content, "final_answer_text")
                root.set_outputs({"answer": message.content})
                return summary

        answer = f"Stopped after {agent_cfg['max_turns']} turns without a final answer."
        summary = runlog.finish(answer, "max_turns")
        root.set_outputs({"answer": answer})
        return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="?", help="question text")
    ap.add_argument("--q", choices=sorted(QUESTIONS), help="a named test question")
    ap.add_argument("--strong-prompt", action="store_true", help="use system_prompt_strong from config.toml")
    ap.add_argument("--config", help="path to a config file (default: config.toml next to this file)")
    args = ap.parse_args(argv)
    question = QUESTIONS.get(args.q) or args.question
    if not question:
        ap.error("give a question or --q <name>")

    tracing.init()
    config = load_config(args.config)
    print(f"Question: {question}\nEndpoint: {config['model']['base_url']}\n")
    summary = run_agent(question, config, strong_prompt=args.strong_prompt)
    print(f"Answer:\n{summary['answer']}\n")
    run_dir = summary.get("run_dir")
    print(f"Payloads saved in {run_dir}\nView them with: python payloads.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
