"""Which version of the agent is running, for labelling traces and evaluations in MLflow.

A version is named after the module start it matches, the state reset.py builds:

    kestrel-m4-start            the files are exactly module 4's starting state
    kestrel-m4-start-modified   the participant has edited them since

The base for "modified" is the module last reset to (reset.py notes it in .lab-state),
or module 1 for a checkout that has never been reset. Only the files the lab itself
changes between modules are compared: config.toml and the files the solutions supply.

From module 6 on, the lab itself has participants point gateway_url at the lab's gateway
(module 6 by hand, module 7 in its setup cell). That exact address, the one the workbench
gives as LAB_GATEWAY_URL, isn't a participant edit. Any other address is.

    python version.py           print the current version
"""
import os
import pathlib
import re

import reset

HERE = reset.HERE
STATE = HERE / ".lab-state"


def _lab_files():
    return sorted({"config.toml", *(f.name for f in (HERE / "solutions").glob("module-*/*.py"))})


def _module_start(module, head):
    """The contents reset.py would leave in each file for this module's start."""
    files = dict(head)
    if module >= 3:
        files["config.toml"] = files["config.toml"].decode().replace(reset.MISMATCHED, reset.VALIDATED).encode()
    for earlier in range(3, module):
        for f in (HERE / "solutions" / f"module-{earlier:02d}").glob("*.py"):
            files[f.name] = f.read_bytes()
    return files


def _without_lab_gateway(config):
    """config.toml with gateway_url set back to empty if it holds the lab's own gateway address."""
    lab = os.environ.get("LAB_GATEWAY_URL")
    if not lab or config is None:
        return config
    line = re.compile(r"""^gateway_url[ \t]*=[ \t]*(["'])""" + re.escape(lab) + r"""\1[ \t]*$""", re.MULTILINE)
    return line.sub('gateway_url = ""', config.decode()).encode()


def _last_reset():
    try:
        module = int(STATE.read_text().strip())
        return module if module in reset.MODULES else None
    except (OSError, ValueError):
        return None


def current():
    """The version name, or None when it can't be told (for example, not a git checkout)."""
    try:
        names = _lab_files()
        head = {name: reset.git("show", f"HEAD:./{name}").encode() for name in names}
        now = {name: (HERE / name).read_bytes() if (HERE / name).is_file() else None for name in names}
        last = _last_reset()
        if last and last >= 6:
            now["config.toml"] = _without_lab_gateway(now["config.toml"])
        matches = [m for m in reset.MODULES if _module_start(m, head) == now]
    except Exception:
        return None
    if matches:
        return f"kestrel-m{last if last in matches else matches[0]}-start"
    return f"kestrel-m{last or 1}-start-modified"


def note_reset(module):
    """Called by reset.py: remember which module start the checkout was put in."""
    try:
        STATE.write_text(f"{module}\n")
    except OSError:
        pass


if __name__ == "__main__":
    print(current() or "unknown (not a git checkout of the lab)")
