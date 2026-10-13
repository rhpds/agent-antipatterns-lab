"""Chooses where the agent's tools come from: built in (tools.py) or the gateway."""
import tools
from gateway import Gateway


class Toolbox:
    def __init__(self, definitions, call, source):
        self.definitions = definitions
        self.call = call          # call(name, arguments_dict) -> dict
        self.source = source      # "local" or the gateway URL


def open_toolbox(config):
    url = config.get("tools", {}).get("gateway_url", "")
    if url:
        gw = Gateway(url)
        return Toolbox(gw.list_tools(), gw.call_tool, url)
    return Toolbox(tools.TOOL_DEFINITIONS, tools.run_tool, "local")
