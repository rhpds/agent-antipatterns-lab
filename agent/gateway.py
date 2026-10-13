"""Minimal MCP client for tool discovery through MCP Gateway (module 6).

Speaks JSON-RPC over HTTP POST (MCP streamable-HTTP, plain JSON replies). Tools
are listed again at the start of every run, so a tool registered at the gateway
shows up on the next run with no code change and no restart.
"""
import itertools
import json

import urllib.request

_ids = itertools.count(1)


class Gateway:
    def __init__(self, url, timeout=30):
        self.url = url
        self.timeout = timeout
        self.session_id = None
        self._initialize()

    def _rpc(self, method, params=None, notify=False):
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notify:
            payload["id"] = next(_ids)
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # raises on HTTP errors
            body = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            self.session_id = resp.headers.get("Mcp-Session-Id", self.session_id)
        if notify or not body:
            return None
        text = body.decode()
        if content_type.startswith("text/event-stream"):
            text = next(line[5:] for line in text.splitlines() if line.startswith("data:"))
        reply = json.loads(text)
        if "error" in reply:
            raise RuntimeError(f"gateway error: {reply['error']}")
        return reply["result"]

    def _initialize(self):
        self._rpc("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "kestrel-agent", "version": "1.0"},
        })
        self._rpc("notifications/initialized", notify=True)

    def list_tools(self):
        """Return the catalog as OpenAI-style tool definitions."""
        tools = self._rpc("tools/list")["tools"]
        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        } for t in tools]

    def call_tool(self, name, arguments):
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        try:
            return json.loads(text)
        except ValueError:
            return {"text": text, "isError": result.get("isError", False)}
