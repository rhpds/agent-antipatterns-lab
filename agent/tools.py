"""Tool definitions, tool implementations, and the wrapper that runs them.

Kestrel Industrial is fictional; the data these tools read lives in fixtures/.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).parent


def _load(name):
    return json.loads((HERE / "fixtures" / name).read_text())


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
    return {"results": [
        {"part_number": p["part_number"], "name": p["name"], "products": p["products"]}
        for _, p in results[:3]
    ]}


def check_stock(part_number, depot):
    if not part_number.startswith("KI-"):
        raise ValueError("part_number must be a Kestrel part number such as KI-XX-00000")
    data = _load("stock.json")
    known = {d.lower(): d for d in data["depots"]}
    depot_name = known.get(depot.lower())  # None for a depot we do not know
    rows = []
    for row in data["stock"]:
        if row["part_number"] != part_number or row["qty"] <= 0:
            continue
        if depot_name and row["depot"] != depot_name:
            continue
        rows.append({"depot": row["depot"], "qty": row["qty"], "lead_days": row["lead_days"]})
    return {"results": rows}


# --- The registry the loop uses --------------------------------------------------

TOOL_FUNCTIONS = {
    "find_part": find_part,
    "check_stock": check_stock,
}


def run_tool(name, arguments):
    """Run one tool and always hand the loop something it can use."""
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except Exception:
        return {"results": []}
