"""Local mock of MCP Gateway for module 6. Stdlib only; dev/test tool.

    python mock_gateway.py --agent-dir <agent copy> --port 8103 [--prefix kestrel_]

Serves the agent's own tools (from <agent-dir>/tools.py) over MCP JSON-RPC. The
catalog starts without estimate_delivery; register it the way a platform operator
would, with no change to the agent:

    curl -X POST http://127.0.0.1:8103/_admin/register -d '{"tool": "estimate_delivery"}'
"""
import argparse
import importlib
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def build(agent_dir, prefix):
    sys.path.insert(0, agent_dir)
    tools = importlib.import_module("tools")
    delivery = importlib.import_module("estimate_delivery")
    catalog = {}   # bare name -> (definition, function)
    for d in tools.TOOL_DEFINITIONS:
        catalog[d["function"]["name"]] = (d, lambda a, n=d["function"]["name"]: tools.run_tool(n, a))
    available = {"estimate_delivery": (delivery.DEFINITION, lambda a: delivery.estimate_delivery(**a))}
    state = {"catalog": catalog}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body=None, headers=None):
            data = json.dumps(body).encode() if body is not None else b""
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Mcp-Session-Id", "mock-session")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            msg = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/_admin/register":
                name = msg["tool"]
                state["catalog"][name] = available[name]
                return self._send(200, {"registered": name})
            method, rid = msg.get("method"), msg.get("id")
            if method == "initialize":
                result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "mock-gateway", "version": "0"}}
            elif method == "notifications/initialized":
                return self._send(202)
            elif method == "tools/list":
                result = {"tools": [{"name": prefix + n, "description": d["function"]["description"],
                                     "inputSchema": d["function"]["parameters"]}
                                    for n, (d, _) in state["catalog"].items()]}
            elif method == "tools/call":
                name = msg["params"]["name"][len(prefix):]
                out = state["catalog"][name][1](msg["params"].get("arguments") or {})
                result = {"content": [{"type": "text", "text": json.dumps(out)}], "isError": False}
            else:
                return self._send(200, {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": method}})
            self._send(200, {"jsonrpc": "2.0", "id": rid, "result": result})

        def log_message(self, fmt, *args):
            pass

    return Handler


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-dir", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    ThreadingHTTPServer(("127.0.0.1", a.port), build(a.agent_dir, a.prefix)).serve_forever()
