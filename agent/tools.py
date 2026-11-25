"""Tool definitions, tool implementations, and the wrapper that runs them.

Kestrel Industrial is fictional; the data these tools read lives in fixtures/.
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
    return {"results": [
        {"part_number": p["part_number"], "name": p["name"], "products": p["products"]}
        for _, p in results[:3]
    ]}


def check_stock(part_number, depot):
    # Kestrel part numbers start with KI-; anything else is refused.
    if not part_number.startswith("KI-"):
        raise ValueError("part_number must be a Kestrel part number such as KI-XX-00000")
    data = _load("stock.json")
    # The depot names, looked up without caring about upper or lower case.
    known = {d.lower(): d for d in data["depots"]}
    depot_name = known.get(depot.lower())  # None for a depot we do not know
    rows = []
    for row in data["stock"]:
        # Only this part, and only where some are in stock.
        if row["part_number"] != part_number or row["qty"] <= 0:
            continue
        # With a known depot, only that depot's rows.
        if depot_name and row["depot"] != depot_name:
            continue
        rows.append({"depot": row["depot"], "qty": row["qty"], "lead_days": row["lead_days"]})
    return {"results": rows}


# --- The registry the loop uses --------------------------------------------------
# Each tool's name, as the model knows it, and the function that runs it.

TOOL_FUNCTIONS = {
    "find_part": find_part,
    "check_stock": check_stock,
}


def run_tool(name, arguments):
    """Run one tool and always hand the loop something it can use."""
    # Look the tool up by name and call it with the model's arguments. `**arguments`
    # passes each value in the dict as a named argument, e.g. query="coolant pump".
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    # If that raises an error of any kind, return an empty list of results instead.
    except Exception:
        return {"results": []}
