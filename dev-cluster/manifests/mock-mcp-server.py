import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# "id" alongside "name" is required — a broker-specific extension beyond the
# vanilla MCP spec. Omitting it makes the broker log "tool id is missing" and
# silently drop the server's tools.
TOOLS = [
    {
        "id": "public_echo",
        "name": "public_echo",
        "description": "Echo back the given text. Available to all identities.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "id": "admin_reset",
        "name": "admin_reset",
        "description": "Reset the demo counter. Admin-only tool.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

COUNTER = {"value": 0}


def call_tool(name, args):
    if name == "public_echo":
        return {"content": [{"type": "text", "text": args.get("text", "")}]}
    if name == "admin_reset":
        COUNTER["value"] = 0
        return {"content": [{"type": "text", "text": "counter reset"}]}
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
                "serverInfo": {"name": "rh1-demo-mcp-server", "version": "0.1.0"},
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
            # The Gateway's own oauth2-proxy forwards the caller's Kubernetes
            # identity via X-Auth-Request-User (system:serviceaccount:ns:name).
            # This is the real, working mechanism for identity-based tool
            # filtering — no custom AuthPolicy plumbing needed to get a per-
            # caller tool set.
            identity = self.headers.get("X-Auth-Request-User", "")
            is_admin = identity.endswith(":rh1-mcp-admin")
            tools = TOOLS if is_admin else [t for t in TOOLS if t["id"] != "admin_reset"]
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
