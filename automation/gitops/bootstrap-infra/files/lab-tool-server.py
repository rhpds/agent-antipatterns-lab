"""The lab's tool server behind MCP Gateway (module 6). Standard library only.

It serves the agent's own tools, exactly as participants have them at the start of module 6
(module 5's tools.py: find_part and check_stock with module 4's error contract, plus
search_bulletins), by importing them from a clone of the lab repo at LAB_AGENT_DIR. So what
the gateway serves can't drift from what participants built.

- search_bulletins answers from this server's own read-only copy of the service bulletins,
  indexed in memory at startup with the agent's own chunking and embedding, because a shared
  server can't reach each participant's own database. Results use the same contract and
  scores as agent/retrieval.py.
- estimate_delivery is listed, and callable, only for a participant whose project has
  registered it: a ConfigMap named kestrel-tool-registrations in their project, with the
  tool's name as a key. Who is calling comes from an identity header the gateway adds after
  authenticating the caller or, failing that, from a Kubernetes TokenReview of the caller's
  own bearer token, which the broker passes on with userSpecificList enabled.

MCP over HTTP POST, plain JSON replies. The broker needs "ping" and an "id" on every tool.
"""
import importlib
import json
import math
import os
import ssl
import sys
import threading
import time
import types
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AGENT_DIR = os.environ.get("LAB_AGENT_DIR", "/src/agent")
REGISTRATION_CONFIGMAP = os.environ.get("LAB_REGISTRATION_CONFIGMAP", "kestrel-tool-registrations")
REGISTRABLE = {"estimate_delivery"}
IDENTITY_HEADERS = [h.strip().lower() for h in os.environ.get(
    "LAB_IDENTITY_HEADERS", "x-auth-request-user,x-forwarded-user,x-remote-user").split(",") if h.strip()]
USER_NAMESPACE_SUFFIX = os.environ.get("LAB_USER_NAMESPACE_SUFFIX", "-app")
# Tests only: the project assumed for a caller with no identity header, and registrations read
# from a JSON file ({"<project>": ["estimate_delivery"]}) instead of the Kubernetes API.
ANONYMOUS_NAMESPACE = os.environ.get("LAB_ANONYMOUS_NAMESPACE")
REGISTRATIONS_FILE = os.environ.get("LAB_REGISTRATIONS_FILE")
SA_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"


def load_agent():
    """Import the agent's tool modules. retrieval.py and ingest_corpus.py import psycopg at the
    top; this server never connects to a database, so a stand-in module is enough."""
    sys.path.insert(0, AGENT_DIR)
    try:
        importlib.import_module("psycopg")
    except ImportError:
        stub = types.ModuleType("psycopg")
        stub.Error = Exception
        sys.modules["psycopg"] = stub
    tools = importlib.import_module("tools")
    retrieval = importlib.import_module("retrieval")
    ingest = importlib.import_module("ingest_corpus")
    delivery = importlib.import_module("estimate_delivery")
    return tools, retrieval, ingest, delivery


TOOLS, RETRIEVAL, INGEST, DELIVERY = load_agent()
INDEX = [(source, section, products, content, RETRIEVAL.embed(to_embed))
         for source, section, products, to_embed, content in INGEST.chunks()]


def search_bulletins(query, product=None, top_k=3):
    """agent/retrieval.py's search_bulletins, over the in-memory copy (same contract, same
    scores: vectors are normalised, so 1 - cosine distance is the dot product)."""
    vec = RETRIEVAL.embed(query)
    rows = [(s, sec, text, sum(a * b for a, b in zip(vec, emb)))
            for s, sec, products, text, emb in INDEX if not product or product.upper() in products]
    rows.sort(key=lambda r: -r[3])
    passages = [{"source": s, "section": sec, "text": text, "score": round(score, 3)}
                for s, sec, text, score in rows[:int(top_k)] if score >= RETRIEVAL.MIN_SCORE]
    if not passages:
        return {"category": "no_results", "retryable": False,
                "detail": f"no bulletin passage matched {query!r}"
                          + (f" for product {product!r}" if product else ""),
                "data": {"passages": []}}
    return {"category": "ok", "retryable": False, "detail": "", "data": {"passages": passages}}


def definitions():
    """Every tool this server can serve, as (OpenAI-style definition, function)."""
    catalog = {}
    for d in TOOLS.TOOL_DEFINITIONS:
        name = d["function"]["name"]
        if name == "search_bulletins":
            catalog[name] = (d, lambda a: search_bulletins(**a))
        else:
            catalog[name] = (d, lambda a, n=name: TOOLS.run_tool(n, a))
    catalog["estimate_delivery"] = (DELIVERY.DEFINITION, lambda a: DELIVERY.estimate_delivery(**a))
    return catalog


CATALOG = definitions()


# --- who is calling, and what they have registered ----------------------------------------

def _kube(method, path, body=None):
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    token = open(f"{SA_DIR}/token").read().strip()
    req = urllib.request.Request(f"https://{host}:{port}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    ctx = ssl.create_default_context(cafile=f"{SA_DIR}/ca.crt")
    with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
        return json.load(resp)


_reviews = {}


def _token_user(authorization):
    """The username behind a bearer token, from a TokenReview (cached for a minute)."""
    if not authorization.lower().startswith("bearer ") or "KUBERNETES_SERVICE_HOST" not in os.environ:
        return None
    token = authorization[7:].strip()
    hit = _reviews.get(token)
    if hit and time.monotonic() - hit[0] < 60:
        return hit[1]
    try:
        status = _kube("POST", "/apis/authentication.k8s.io/v1/tokenreviews",
                       {"apiVersion": "authentication.k8s.io/v1", "kind": "TokenReview",
                        "spec": {"token": token}})["status"]
        user = status["user"]["username"] if status.get("authenticated") else None
    except Exception:
        user = None
    _reviews[token] = (time.monotonic(), user)
    return user


def caller_namespace(headers):
    user = next((headers[h] for h in IDENTITY_HEADERS if headers.get(h)), None)
    user = user or _token_user(headers.get("authorization", ""))
    if not user:
        return ANONYMOUS_NAMESPACE
    if user.startswith("system:serviceaccount:"):
        return user.split(":")[2]
    return user.split("@")[0] + USER_NAMESPACE_SUFFIX


_cache, _lock = {}, threading.Lock()


def registered(namespace):
    """Tools the project has registered, cached for a few seconds."""
    if not namespace:
        return set()
    with _lock:
        hit = _cache.get(namespace)
        if hit and time.monotonic() - hit[0] < 3:
            return hit[1]
    found = set()
    try:
        if REGISTRATIONS_FILE:
            found = set(json.load(open(REGISTRATIONS_FILE)).get(namespace, []))
        else:
            found = set(_kube("GET", f"/api/v1/namespaces/{namespace}/configmaps/{REGISTRATION_CONFIGMAP}")
                        .get("data", {}))
    except Exception:
        found = set()
    found &= REGISTRABLE
    with _lock:
        _cache[namespace] = (time.monotonic(), found)
    return found


def visible(namespace):
    extra = registered(namespace)
    return {n: v for n, v in CATALOG.items() if n not in REGISTRABLE or n in extra}


# --- MCP ------------------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        try:
            msg = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except ValueError:
            msg = {}
        method, rid = msg.get("method"), msg.get("id")
        tools = visible(caller_namespace({k.lower(): v for k, v in self.headers.items()}))
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "kestrel-lab-tools", "version": "1.0"}}
        elif method == "notifications/initialized":
            return self._send(202)
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [{"id": n, "name": n, "description": d["function"]["description"],
                                 "inputSchema": d["function"]["parameters"]} for n, (d, _) in tools.items()]}
        elif method == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name", "")
            if name not in tools:
                result = {"content": [{"type": "text", "text": json.dumps(
                    {"category": "bad_request", "retryable": False,
                     "detail": f"unknown tool {name!r}", "data": None})}], "isError": True}
            else:
                try:
                    out = tools[name][1](params.get("arguments") or {})
                except TypeError as exc:   # the model sent arguments the tool doesn't take
                    out = {"category": "bad_request", "retryable": False, "detail": str(exc), "data": None}
                result = {"content": [{"type": "text", "text": json.dumps(out)}], "isError": False}
        else:
            return self._send(200, {"jsonrpc": "2.0", "id": rid,
                                    "error": {"code": -32601, "message": f"method not found: {method}"}})
        self._send(200, {"jsonrpc": "2.0", "id": rid, "result": result})

    def do_GET(self):
        self._send(200, {"status": "ok", "tools": sorted(CATALOG)} if self.path == "/healthz" else None)

    def log_message(self, fmt, *args):
        print("lab-tool-server:", fmt % args, flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"lab-tool-server: {len(INDEX)} bulletin passages indexed; tools {sorted(CATALOG)}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
