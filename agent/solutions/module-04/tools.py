"""Tool definitions, tool implementations, and the wrapper that runs them.

Module 4 solution: every tool returns the same contract.

    {"category": "ok" | "no_results" | "bad_request" | "upstream_unavailable",
     "retryable": True | False,
     "detail": "what happened, in words",
     "data": {...} or None}
"""
# How this file works
# -------------------
# The agent's tools live here, in three parts:
#   1. TOOL_DEFINITIONS: what the model is told about each tool, its name, what it
#      does and which arguments it takes. This is sent to the model with every request.
#   2. The tools themselves: find_part and check_stock, plain functions that read the
#      fixture data in fixtures/.
#   3. run_tool: what the agent's loop calls when the model asks for a tool. It
#      looks the tool up by name in TOOL_FUNCTIONS, runs it and returns its result.
#
# How a tool call flows: the model replies with a tool name and arguments, the loop in
# agent.py passes them to run_tool, and the result goes back to the loop.
#
# A few pieces of Python you'll meet here:
#   {"name": "find_part", ...}   a dict: named values, looked up by name, e.g. part["name"]
#   [a, b]                       a list: values in order
#   def name(...):               define a function; `return` hands back its result
#   try: ... except ...:         run the `try` block; if it raises an error, run the
#                                `except` block instead
import json
import pathlib

HERE = pathlib.Path(__file__).parent   # the folder this file is in


def _load(name):
    # Read one of the JSON files in fixtures/ into Python dicts and lists.
    return json.loads((HERE / "fixtures" / name).read_text())


def outcome(category, retryable=False, detail="", data=None):
    # One tool result in the contract above (an argument left out takes its default).
    return {"category": category, "retryable": retryable, "detail": detail, "data": data}


# --- What the model is told about each tool -------------------------------------
# Each definition gives the tool's name, a description the model reads to decide when
# to use it, and its parameters: the arguments, their types, and which are required.

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
]


# --- The tools themselves -------------------------------------------------------

def find_part(query, product=None):
    # The words of the query, lower case, with hyphens read as spaces.
    words = set(query.lower().replace("-", " ").split())
    results = []
    for part in _load("parts.json")["parts"]:
        # When a chiller model is given, skip parts that don't fit it.
        if product and product.upper() not in part["products"]:
            continue
        # Score the part by how many of its keywords are in the query; keep any match.
        score = len(words & {k.replace("-", " ") for k in part["keywords"]})
        if score:
            results.append((score, part))
    # Best matches first, then the top three. (A list written as
    # [... for _, p in ...] has one item for each part p.)
    results.sort(key=lambda pair: -pair[0])
    rows = [{"part_number": p["part_number"], "name": p["name"], "products": p["products"]}
            for _, p in results[:3]]
    if not rows:
        return outcome("no_results", detail=f"no part matched {query!r}", data={"results": []})
    return outcome("ok", data={"results": rows})


def check_stock(part_number, depot):
    # Kestrel part numbers start with KI-; anything else is refused.
    if not part_number.startswith("KI-"):
        return outcome("bad_request", detail="part_number must be a Kestrel part number such as KI-XX-00000")
    data = _load("stock.json")
    # The depot names, looked up without caring about upper or lower case.
    known = {d.lower(): d for d in data["depots"]}
    depot_name = known.get(depot.lower())
    if depot_name is None:   # reject instead of silently dropping the filter
        return outcome("bad_request",
                       detail=f"unknown depot {depot!r}; Kestrel depots are {', '.join(data['depots'])}")
    # This part, at this depot, where some are in stock: one row for each match.
    rows = [{"depot": r["depot"], "qty": r["qty"], "lead_days": r["lead_days"]}
            for r in data["stock"]
            if r["part_number"] == part_number and r["depot"] == depot_name and r["qty"] > 0]
    if not rows:
        return outcome("no_results", detail=f"{part_number} has no stock at {depot_name}", data={"results": []})
    return outcome("ok", data={"results": rows})


# --- The registry the loop uses --------------------------------------------------
# Each tool's name, as the model knows it, and the function that runs it.

TOOL_FUNCTIONS = {
    "find_part": find_part,
    "check_stock": check_stock,
}


def run_tool(name, arguments):
    """Run one tool. Failures come back as a categorised outcome, never as an empty success."""
    if name not in TOOL_FUNCTIONS:
        return outcome("bad_request", detail=f"unknown tool {name!r}")
    # Look the tool up by name and call it with the model's arguments. `**arguments`
    # passes each value in the dict as a named argument, e.g. query="coolant pump".
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    # If that raises an error, say which kind of failure it was. `as exc` names the error.
    except TypeError as exc:                       # wrong or missing arguments
        return outcome("bad_request", detail=str(exc))
    except (ConnectionError, TimeoutError) as exc:  # transient: worth one retry
        return outcome("upstream_unavailable", retryable=True, detail=str(exc))
    except Exception as exc:                       # anything else: say what happened, do not retry
        return outcome("upstream_unavailable", detail=f"{type(exc).__name__}: {exc}")
