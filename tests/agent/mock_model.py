"""Local OpenAI-compatible mock of the lab's two vLLM endpoints. Stdlib only.

Dev/test tool, not participant-facing. Adapted from dev-cluster/manifests/mock-target.py.

    python mock_model.py --mode mismatched --port 8101
    python mock_model.py --mode validated  --port 8102

mismatched  Reproduces module 2's fault. HTTP 200, `tool_calls` empty, finish_reason
            "stop", and the hermes-format <tool_call>{...}</tool_call> text left in
            `content` next to a confident, invented answer.
validated   Proper `tool_calls` and finish_reason "tool_calls" when a tool is needed,
            plain text once the conversation holds the tool results it needs.

The model is scripted, keyed on the question, but it only acts on what is in the
request: with no tool results in `messages` it asks for the first tool again, which
is what a real greedy-decoded model does when a loop discards results.

NOTE: the invented part numbers below are NOT Kestrel fixture data.
"""
import argparse
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

INVENTED = {
    "m1": "The replacement coolant pump for the K-400 is part number KC-4400-P12. "
          "Replace it and bleed the coolant loop afterwards.",
    "m3": "Yes, a K-400 coolant pump (KC-4400-P12) is in stock at Denver and can ship this week.",
    "m4": "Yes, the K-600 high-pressure sensor (KC-6000-HS4) is available at the Portland depot.",
    "m5": "Fault F-21 on a K-400 means the temperature sensor has failed. Replace the sensor "
          "(KC-4400-TS2) and reset the controller.",
    "m5-miss": "The Kestrel K-900 should be serviced every 3,000 operating hours.",
    "m6": "Shipping from Denver to Boulder typically takes two to three business days.",
}


def bare(name):
    """Tool name without any gateway prefix, e.g. 'kestrel_find_part' -> 'find_part'."""
    for base in ("find_part", "check_stock", "search_bulletins", "estimate_delivery"):
        if name.endswith(base):
            return base
    return name


def classify(question):
    q = question.lower()
    if "k-900" in q:
        return "m5-miss"
    if "boulder" in q:
        return "m6"
    if "f-21" in q:
        return "m5"
    if "depot" in q and "available" in q:
        return "m4"
    if "denver" in q:
        return "m3"
    if "part number" in q and "coolant" in q:
        return "m1"
    return None


def tool_results(messages):
    """[(bare tool name, parsed result)] in order, from role=tool messages."""
    names = {}
    for m in messages:
        for c in m.get("tool_calls") or []:
            names[c["id"]] = c["function"]["name"]
    out = []
    for m in messages:
        if m["role"] == "tool":
            try:
                out.append((bare(names.get(m.get("tool_call_id"), "")), json.loads(m["content"])))
            except ValueError:
                out.append(("?", {}))
    return out


def rows(result):
    """Result rows in either the starter shape ({'results': []}) or the contract shape."""
    if "data" in result:
        return ((result.get("data") or {}).get("results")) or []
    return result.get("results") or []


def failed(result):
    return result.get("category") not in (None, "ok", "no_results")


def plan(intent, offered, results, question):
    """Return ('tool', bare_name, args) or ('text', text), as a validated model would."""
    names = [n for n, _ in results]
    depot = (re.search(r"at the (\w+) depot", question) or re.search(r"(Denver)", question))
    depot = depot.group(1) if depot else "Denver"

    if intent == "m1":
        if "find_part" not in names:
            return ("tool", "find_part", {"query": "coolant pump", "product": "K-400"})
        part = rows(results[0][1])
        return ("text", f"The replacement coolant pump for the K-400 is part number {part[0]['part_number']}."
                if part else "I could not find that part.")
    if intent in ("m3", "m4"):
        if "find_part" not in names:
            query = "coolant pump" if intent == "m3" else "high-pressure sensor"
            return ("tool", "find_part", {"query": query, "product": "K-400" if intent == "m3" else "K-600"})
        part_rows = rows(results[0][1])
        if "check_stock" not in names:
            return ("tool", "check_stock", {"part_number": part_rows[0]["part_number"], "depot": depot})
        stock = results[names.index("check_stock")][1]
        if failed(stock):
            return ("text", f"I could not complete the stock check: {stock.get('detail')}")
        if rows(stock):
            r = rows(stock)[0]
            return ("text", f"Yes: {r['qty']} in stock at {r['depot']}, lead time {r['lead_days']} day(s).")
        if stock.get("category") == "no_results":
            return ("text", f"There is no stock of that part at {depot}.")
        return ("text", f"No, the part is not available at the {depot} depot.")  # the confident misread
    if intent in ("m5", "m5-miss"):
        if "search_bulletins" not in offered:
            return ("text", INVENTED[intent])
        if "search_bulletins" not in names:
            if intent == "m5":
                return ("tool", "search_bulletins", {"query": "F-21", "product": "K-400"})  # what Qwen3 sends
            return ("tool", "search_bulletins", {"query": "K-900 service interval", "product": "K-900"})
        res = results[names.index("search_bulletins")][1]
        passages = (res.get("data") or {}).get("passages") or []
        if res.get("category") == "ok" and passages:
            # A real model reads every passage, not only the top one.
            return ("text", "According to " + "; ".join(f"{p['source']}: {p['text']}" for p in passages))
        return ("text", f"I could not find that in the service bulletins ({res.get('detail')}). I won't guess.")
    if intent == "m6":
        if "estimate_delivery" not in offered:
            return ("text", INVENTED["m6"])
        if "estimate_delivery" not in names:
            return ("tool", "estimate_delivery", {"origin_depot": "Denver", "destination": "Boulder"})
        res = results[names.index("estimate_delivery")][1]
        d = res.get("data") or {}
        return ("text", f"About {d.get('transit_days')} day(s) from {d.get('origin_depot')} to {d.get('destination')}."
                if res.get("category") == "ok" else f"Could not estimate: {res.get('detail')}")
    return ("text", "I can't help with that request.")


def respond(mode, body):
    messages = body["messages"]
    question = next(m["content"] for m in messages if m["role"] == "user")
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    intent = classify(question)
    offered = {bare(t["function"]["name"]): t["function"]["name"] for t in body.get("tools") or []}
    step = plan(intent, offered, tool_results(messages), question)

    if mode == "validated" and step[0] == "tool":
        _, name, args = step
        call = {"id": f"chatcmpl-tool-{abs(hash((name, json.dumps(args), len(messages)))) % 10**8:08d}",
                "type": "function",
                "function": {"name": offered.get(name, name), "arguments": json.dumps(args)}}
        message = {"role": "assistant", "content": None, "tool_calls": [call]}
        finish = "tool_calls"
    elif mode == "validated":
        message = {"role": "assistant", "content": step[1], "tool_calls": []}
        finish = "stop"
    else:
        # mismatched parser: the call is emitted as text and never parsed
        if step[0] == "tool":
            call_text = json.dumps({"name": step[1], "arguments": step[2]})
        else:
            call_text = json.dumps({"name": "find_part", "arguments": {"query": "coolant pump", "product": "K-400"}})
        lead = "I'll look that up with the find_part tool.\n" if "MUST use" in system else ""
        invented = INVENTED.get(intent, "I can't help with that request.")
        content = f"{lead}<tool_call>\n{call_text}\n</tool_call>\n\n{invented}"
        message = {"role": "assistant", "content": content, "tool_calls": []}
        finish = "stop"
    message["reasoning_content"] = None
    return {
        "id": "chatcmpl-mock", "object": "chat.completion", "created": int(time.time()),
        "model": body.get("model", "mock"),
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def make_handler(mode):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.startswith("/v1/models"):
                self._send(200, {"object": "list", "data": [{"id": "mock", "object": "model"}]})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path.startswith("/v1/chat/completions"):
                if body.get("stream"):  # the lab agent must never stream
                    self._send(400, {"error": "mock: streaming not supported (vLLM #31871)"})
                else:
                    self._send(200, respond(mode, body))
            else:
                self._send(404, {"error": "not found"})

        def log_message(self, fmt, *args):
            pass

    return Handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["mismatched", "validated"], required=True)
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.mode)).serve_forever()
