import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# "id" alongside "name" is required — a broker-specific extension beyond the
# vanilla MCP spec. Omitting it makes the broker log "tool id is missing" and
# silently drop the server's tools.
# PLACEHOLDER server (TODO: replace with the lab's real tool server once the
# Kestrel tools exist). It only exists so the MCP Gateway path can be proven
# end to end. Module 6 registers a further tool (estimate_delivery) by hand.
TOOLS = [
    {
        "id": "echo",
        "name": "echo",
        "description": "Echo back the given text.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]


def call_tool(name, args):
    if name == "echo":
        return {"content": [{"type": "text", "text": args.get("text", "")}]}
    return {"content": [{"type": "text", "text": f"unknown tool: {name}"}], "isError": True}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            req = json.loads(raw)
        except Exception:
            req = {}

        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "lab-placeholder-mcp-server", "version": "0.1.0"},
            }
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": result})
        elif method == "notifications/initialized":
            self.send_response(202)
            self.end_headers()
        elif method == "ping":
            # Required — the broker health-checks upstream servers with this and
            # marks them unhealthy (dropping all their tools, with no
            # client-visible error) if it isn't implemented.
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {}})
        elif method == "tools/list":
            tools = TOOLS
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            result = call_tool(name, args)
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": result})
        else:
            self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "method not found"}})

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print("mcp-server:", fmt % args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()
