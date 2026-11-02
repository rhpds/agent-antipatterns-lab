"""Module 6 through the lab's real gateway (acceptance/lab/module6-gateway.feature).

The lab's tool server (automation/gitops/bootstrap-infra/files/lab-tool-server.py) runs here
as it does on the cluster: a copy of the agent with module 5's tools.py in place, its own
in-memory copy of the bulletins, and registrations read per project. A JSON file stands in
for the Kubernetes API, and LAB_ANONYMOUS_NAMESPACE for the identity the gateway would add.
The agent talks to it directly; the gateway's broker only proxies and adds a prefix, which
the mock-gateway tests cover.
"""
import json
import shutil
import subprocess
import sys
import urllib.request

import pytest

from conftest import AGENT, REPO, free_port, wait_for

SERVER = REPO / "automation" / "gitops" / "bootstrap-infra" / "files" / "lab-tool-server.py"


@pytest.fixture
def lab_server(tmp_path):
    src = tmp_path / "server-agent"
    shutil.copytree(AGENT, src, ignore=shutil.ignore_patterns("runs", "__pycache__"))
    shutil.copy(src / "solutions" / "module-05" / "tools.py", src / "tools.py")   # as the init container does
    registrations = tmp_path / "registrations.json"
    registrations.write_text("{}")
    port = free_port()
    env = {"PATH": "/usr/bin:/bin", "PORT": str(port), "LAB_AGENT_DIR": str(src),
           "LAB_REGISTRATIONS_FILE": str(registrations), "LAB_ANONYMOUS_NAMESPACE": "lab-test"}
    proc = subprocess.Popen([sys.executable, str(SERVER)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_for(f"http://127.0.0.1:{port}/healthz")
    yield f"http://127.0.0.1:{port}/mcp", registrations
    proc.terminate()


def register(registrations, namespace, tool="estimate_delivery"):
    """What the participant's notebook cell does: one ConfigMap in their own project."""
    current = json.loads(registrations.read_text())
    current.setdefault(namespace, []).append(tool)
    registrations.write_text(json.dumps(current))


def tool_names(url, identity=None):
    headers = {"Content-Type": "application/json"}
    if identity:
        headers["X-Auth-Request-User"] = identity
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=10) as resp:
        return sorted(t["name"] for t in json.load(resp)["result"]["tools"])


def test_the_agent_reaches_its_tools_through_the_lab_gateway(work, lab_server):
    """Scenario: The agent reaches its tools through the lab's gateway"""
    url, _ = lab_server
    work.repoint_to_validated()
    work.apply_solution("module-05")
    local, _ = work.agent("m3")
    work.set_gateway(url)
    through, _ = work.agent("m3")
    assert through["ended_by"] == local["ended_by"] and through["turns"] == local["turns"]
    assert [t["name"] for t in through["tool_calls"]] == [t["name"] for t in local["tool_calls"]]
    assert [t["result"] for t in through["tool_calls"]] == [t["result"] for t in local["tool_calls"]]
    assert sorted(through["tools_offered"]) == ["check_stock", "find_part", "search_bulletins"]


def test_search_through_the_gateway_still_cites_the_service_bulletin(work, lab_server):
    """Scenario: Search through the gateway still cites the service bulletin"""
    url, _ = lab_server
    work.repoint_to_validated()
    work.apply_solution("module-05")
    work.set_gateway(url)
    summary, _ = work.agent("m5")
    search = [t for t in summary["tool_calls"] if t["name"].endswith("search_bulletins")]
    assert search and search[0]["result"]["category"] == "ok"
    assert "SB-2024-102" in [p["source"] for p in search[0]["result"]["data"]["passages"]]
    assert "SB-2024-102" in summary["answer"] or "coolant loop pressure low" in summary["answer"].lower()


def test_registering_the_delivery_tool_changes_only_that_participants_catalog(lab_server):
    """Scenario: Registering the delivery tool changes only that participant's catalog"""
    url, registrations = lab_server
    one, other = "system:serviceaccount:user1-app:kestrel-agent", "user2"
    assert "estimate_delivery" not in tool_names(url, one) and "estimate_delivery" not in tool_names(url, other)
    register(registrations, "user1-app")
    import time
    time.sleep(3.5)                                  # the server caches registrations for 3 s
    assert "estimate_delivery" in tool_names(url, one)
    assert "estimate_delivery" not in tool_names(url, other)
    register(registrations, "user2-app")
    time.sleep(3.5)
    assert "estimate_delivery" in tool_names(url, other)


def test_module7_passes_every_case_on_a_lab_environment(work, lab_server):
    """Scenario: Module 7 passes every case on a lab environment"""
    url, registrations = lab_server
    work.repoint_to_validated()
    work.apply_solution("module-05")
    work.set_gateway(url)
    register(registrations, "lab-test")
    out = work.run("regression.py").stdout
    assert "6 passed, 0 failed, 0 skipped" in out, out
