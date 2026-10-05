"""The estimate_delivery tool (module 6).

It is NOT built into the agent. It is registered at the MCP Gateway during module 6
and the agent discovers it at runtime. This file is the implementation the lab's
MCP server exposes; the agent never imports it.
"""
import json
import pathlib

DEFINITION = {
    "type": "function",
    "function": {
        "name": "estimate_delivery",
        "description": "Estimate how many days a shipment takes from a Kestrel depot to a customer site city.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin_depot": {"type": "string", "description": "Depot name, e.g. Denver"},
                "destination": {"type": "string", "description": "Customer site city, e.g. Boulder"},
            },
            "required": ["origin_depot", "destination"],
        },
    },
}


def estimate_delivery(origin_depot, destination):
    table = json.loads((pathlib.Path(__file__).parent / "fixtures" / "delivery.json").read_text())["transit_days"]
    lanes = {d.lower(): (d, cities) for d, cities in table.items()}
    if origin_depot.lower() not in lanes:
        return {"category": "bad_request", "retryable": False,
                "detail": f"unknown depot {origin_depot!r}; depots are {', '.join(table)}", "data": None}
    depot, cities = lanes[origin_depot.lower()]
    days = {c.lower(): n for c, n in cities.items()}.get(destination.lower())
    if days is None:
        return {"category": "no_results", "retryable": False,
                "detail": f"no delivery lane from {depot} to {destination!r}", "data": None}
    return {"category": "ok", "retryable": False, "detail": "",
            "data": {"origin_depot": depot, "destination": destination, "transit_days": days}}
