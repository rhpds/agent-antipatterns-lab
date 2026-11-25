"""The tools the agent is offered, and how it calls them (both from tools.py)."""
import tools


class Toolbox:
    def __init__(self, definitions, call, source):
        self.definitions = definitions
        self.call = call          # call(name, arguments_dict) -> dict
        self.source = source      # where the tools come from: "local", the built-in tools.py


def open_toolbox(config):
    return Toolbox(tools.TOOL_DEFINITIONS, tools.run_tool, "local")
