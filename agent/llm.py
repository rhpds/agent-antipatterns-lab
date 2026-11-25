"""The one place the agent talks to the model.

Chat Completions API, NON-streaming. Streaming is deliberately not used: upstream
vLLM issue #31871 reports the hermes parser returning raw text instead of parsed
tool_calls when streaming, which would make a correct fix look broken.

To move to the Responses API later, only call_model() below needs to change.
"""
import os

import openai


def call_model(config, messages, tools, runlog, n):
    """Send one request, save the raw request and response, return the parsed completion."""
    model = config["model"]
    body = {
        "model": model["name"],
        "messages": messages,
        "temperature": model.get("temperature", 0),
        "seed": model.get("seed", 0),
        "max_tokens": model.get("max_tokens", 1024),
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    runlog.save_request(n, body)

    client = openai.OpenAI(
        base_url=model["base_url"],
        api_key=os.environ.get(model.get("api_key_env", "OPENAI_API_KEY"), "EMPTY"),
        timeout=model.get("timeout_seconds", 120),
        max_retries=0,
    )
    try:
        raw = client.chat.completions.with_raw_response.create(**body)
    except openai.APIStatusError as exc:
        runlog.save_response(n, exc.response.text, exc.status_code)
        raise
    runlog.save_response(n, raw.http_response.text)  # the wire, not our re-serialisation
    completion = raw.parse()
    choice = completion.choices[0]
    runlog.add_model_call(n, choice.finish_reason, len(choice.message.tool_calls or []))
    return completion
