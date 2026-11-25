"""Kestrel field service parts agent.

    python agent.py --q m1                       # run a named test question
    python agent.py "your own question"
    python agent.py --q m1 --strong-prompt       # use the stronger system prompt

Three files matter: tools.py (tool definitions), this file (the loop), and
config.toml (which model endpoint to call). Every run saves the raw request and
response of each model call under runs/; see payloads.py.
"""
# How this file works
# -------------------
# This is the agent itself: a loop that sends a question to a model, runs the tools
# the model asks for, and decides when the run is over.
#
# One run, step by step (all of it is in run_agent below):
#   1. Build the conversation: the system prompt (the model's instructions), then the question.
#   2. Each turn, send the conversation to the model and read its reply.
#   3. If the reply asks for tools, run each one and note the result in the run log.
#   4. Decide whether to stop. If not, go round again, up to max_turns times.
#
# What to read: run_agent, and its loop in particular. The three small helpers under
# it (ask_model, use_tool and end_run) each do one step and record it for the trace
# view in MLflow. main(), at the bottom, reads the command line and prints the result.
#
# A few pieces of Python you'll meet here:
#   {"role": "user", "content": question}   a dict: named values. config["agent"] looks
#                                            up the value named "agent" in the dict config
#   [a, b]                                   a list: values in order
#   for x in things:                         repeat the indented block once per item
#   with tracing.span(...) as span:          run the indented block inside a trace span,
#                                            which closes when the block ends
#   def name(...):                           define a function; `return` hands back its result

# Other files this one uses. Each `import` makes another file's code available here.
import argparse
import json
import pathlib
import sys
import tomllib
from urllib.parse import urlparse

import tracing
from llm import call_model
from questions import QUESTIONS
from runlog import RunLog
from toolbox import open_toolbox

# config.toml, in the same folder as this file.
DEFAULT_CONFIG = pathlib.Path(__file__).parent / "config.toml"


def load_config(path=None):
    # Read config.toml (or the file at `path`, if one is given) into a dict.
    with open(path or DEFAULT_CONFIG, "rb") as f:
        return tomllib.load(f)


def run_agent(question, config, strong_prompt=False, runs_dir=None):
    """Run the agent on one question. Returns the run summary (also saved as summary.json)."""
    # The [agent] section of config.toml, and the system prompt from it: the stronger
    # one when strong_prompt is True, otherwise the default one.
    agent_cfg = config["agent"]
    system = agent_cfg["system_prompt_strong" if strong_prompt else "system_prompt"]

    # The conversation the model sees: its instructions, then the question.
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]

    # The run log saves every request and response under runs/. The toolbox holds the
    # tools the model is offered, and the run log notes their names. (A list written as
    # [... for d in ...] has one item for each d.)
    runlog = RunLog(question, config["model"]["base_url"], runs_dir)
    toolbox = open_toolbox(config)
    runlog.tools_offered = [d["function"]["name"] for d in toolbox.definitions]

    # The whole run is one trace in MLflow, and `root` is its top-level span.
    with tracing.span("agent_run", "AGENT", inputs={"question": question}) as root:
        # Turn 1, 2, 3 ... up to max_turns from config.toml.
        for turn in range(1, agent_cfg["max_turns"] + 1):
            # Send the conversation to the model and take its reply.
            choice = ask_model(config, messages, toolbox, runlog, turn)
            message = choice.message   # what the model said: its text and any tool calls

            # No tool calls: the model answered in plain text, so stop.
            if not message.tool_calls:
                return end_run(root, runlog, message.content, "plain_answer")

            # Run each tool the model asked for, with the arguments it chose.
            for call in message.tool_calls:
                arguments = json.loads(call.function.arguments)
                result = use_tool(toolbox, call.function.name, arguments)
                runlog.add_tool_call(call.function.name, arguments, result)

            # Stop if the model says it has a final answer.
            if "final answer" in (message.content or "").lower():
                return end_run(root, runlog, message.content, "final_answer_text")

        # Every turn was used without the run ending: stop and say so.
        answer = f"Stopped after {agent_cfg['max_turns']} turns without a final answer."
        return end_run(root, runlog, answer, "max_turns")


# --- The steps run_agent uses, each recorded in the trace ------------------------

def ask_model(config, messages, toolbox, runlog, turn):
    """Send the messages and the tool definitions to the model. Returns its reply."""
    # The model call is a span in the trace. list(messages) records a copy of the
    # messages as they were when this request was sent.
    with tracing.span(f"model_call_{turn}", "CHAT_MODEL", inputs={"messages": list(messages), "tools_offered": runlog.tools_offered}) as llm_span:
        response = call_model(config, messages, toolbox.definitions, runlog, turn)
        choice = response.choices[0]   # we ask for one reply, so take the first
        tracing.record_model_call(llm_span, response)
    return choice


def use_tool(toolbox, name, arguments):
    """Run one tool with the given arguments. Returns what the tool returned."""
    # The tool call is a span in the trace, with the arguments in and the result out.
    with tracing.span(name, "TOOL", inputs=arguments) as tool_span:
        result = toolbox.call(name, arguments)
        tool_span.set_outputs(result)
    return result


def end_run(root, runlog, answer, ended_by):
    """End the run: save summary.json, put the outcome on the trace, return the summary."""
    summary = runlog.finish(answer, ended_by)
    tracing.record_run(root, summary)
    return summary


# --- Running it from the command line --------------------------------------------

def main(argv=None):
    # The command-line options: a question (or --q and a test question's name),
    # --strong-prompt and --config.
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="?", help="question text")
    ap.add_argument("--q", choices=sorted(QUESTIONS), help="a named test question")
    ap.add_argument("--strong-prompt", action="store_true", help="use system_prompt_strong from config.toml")
    ap.add_argument("--config", help="path to a config file (default: config.toml next to this file)")
    args = ap.parse_args(argv)
    question = QUESTIONS.get(args.q) or args.question
    if not question:
        ap.error("give a question or --q <name>")

    # Switch tracing on (when MLflow is set up), and tag this run's trace with the
    # endpoint, the prompt and the question, so the trace list can filter by them.
    tracing.init()
    config = load_config(args.config)
    endpoint = urlparse(config["model"]["base_url"]).hostname or config["model"]["base_url"]
    tracing.set_run_tags(endpoint=endpoint.split(".")[0].removesuffix("-predictor"),
                         prompt="strong" if args.strong_prompt else "default",
                         question=args.q or "your own")

    # Run the agent and print the answer and where the run was saved.
    # The endpoint is an address inside the cluster. Print it without "http://", or a
    # notebook turns it into a link that a browser can't open.
    address = config["model"]["base_url"].split("://", 1)[-1]
    print(f"Question: {question}\nEndpoint: {address} (inside the cluster)\n")
    summary = run_agent(question, config, strong_prompt=args.strong_prompt)
    print(f"Answer:\n{summary['answer']}\n")
    run_dir = summary.get("run_dir")
    print(f"Payloads saved in {run_dir}\nView them with: python payloads.py")
    tracing.report(summary)
    return 0


# Run main() when this file is started with `python agent.py`, but not when another
# file imports it.
if __name__ == "__main__":
    sys.exit(main())
