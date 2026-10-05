"""Tool definitions, tool implementations, and the wrapper that runs them.

Module 4 + 5 solution: every tool returns the same contract.

    {"category": "ok" | "no_results" | "bad_request" | "upstream_unavailable",
     "retryable": True | False,
     "detail": "what happened, in words",
     "data": {...} or None}
"""
import json
import pathlib

from retrieval import SEARCH_BULLETINS_DEFINITION, search_bulletins

HERE = pathlib.Path(__file__).parent


def _load(name):
    return json.loads((HERE / "fixtures" / name).read_text())


def outcome(category, retryable=False, detail="", data=None):
    return {"category": category, "retryable": retryable, "detail": detail, "data": data}


# --- What the model is told about each tool -------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "find_part",
            "description": "Find Kestrel replacement part numbers from a symptom or "
                           "description and a chiller model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Symptom or part description, e.g. 'coolant pump'"},
                    "product": {"type": "string", "description": "Chiller model, e.g. K-400"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Check stock and lead time for a part number at a depot. "
                           "Takes a part number from find_part, not a description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_number": {"type": "string", "description": "Part number, e.g. KI-XX-00000"},
                    "depot": {"type": "string", "description": "Depot name, e.g. Denver"},
                },
                "required": ["part_number", "depot"],
            },
        },
    },
    SEARCH_BULLETINS_DEFINITION,   # module 5: the retrieval tool is now registered
]


# --- The tools themselves -------------------------------------------------------

def find_part(query, product=None):
    words = set(query.lower().replace("-", " ").split())
    results = []
    for part in _load("parts.json")["parts"]:
        if product and product.upper() not in part["products"]:
            continue
        score = len(words & {k.replace("-", " ") for k in part["keywords"]})
        if score:
            results.append((score, part))
    results.sort(key=lambda pair: -pair[0])
    rows = [{"part_number": p["part_number"], "name": p["name"], "products": p["products"]}
            for _, p in results[:3]]
    if not rows:
        return outcome("no_results", detail=f"no part matched {query!r}", data={"results": []})
    return outcome("ok", data={"results": rows})


def check_stock(part_number, depot):
    if not part_number.startswith("KI-"):
        return outcome("bad_request", detail="part_number must be a Kestrel part number such as KI-XX-00000")
    data = _load("stock.json")
    known = {d.lower(): d for d in data["depots"]}
    depot_name = known.get(depot.lower())
    if depot_name is None:   # reject instead of silently dropping the filter
        return outcome("bad_request",
                       detail=f"unknown depot {depot!r}; Kestrel depots are {', '.join(data['depots'])}")
    rows = [{"depot": r["depot"], "qty": r["qty"], "lead_days": r["lead_days"]}
            for r in data["stock"]
            if r["part_number"] == part_number and r["depot"] == depot_name and r["qty"] > 0]
    if not rows:
        return outcome("no_results", detail=f"{part_number} has no stock at {depot_name}", data={"results": []})
    return outcome("ok", data={"results": rows})


# --- The registry the loop uses --------------------------------------------------

TOOL_FUNCTIONS = {
    "find_part": find_part,
    "check_stock": check_stock,
    "search_bulletins": search_bulletins,
}


def run_tool(name, arguments):
    """Run one tool. Failures come back as a categorised outcome, never as an empty success."""
    if name not in TOOL_FUNCTIONS:
        return outcome("bad_request", detail=f"unknown tool {name!r}")
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except TypeError as exc:                       # wrong or missing arguments
        return outcome("bad_request", detail=str(exc))
    except (ConnectionError, TimeoutError) as exc:  # transient: worth one retry
        return outcome("upstream_unavailable", retryable=True, detail=str(exc))
    except Exception as exc:                       # anything else: say what happened, do not retry
        return outcome("upstream_unavailable", detail=f"{type(exc).__name__}: {exc}")
