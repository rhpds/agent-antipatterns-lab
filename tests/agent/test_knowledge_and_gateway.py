"""Modules 5-7: pgvector retrieval (throwaway podman container), gateway discovery, full regression."""
import json
import shutil
import subprocess
import sys
import time
import urllib.request

import pytest

from conftest import AGENT, HERE, fixture_part, free_port, read_json, spawn, wait_for

IMAGE = "docker.io/pgvector/pgvector:pg16"


@pytest.fixture(scope="session")
def pg():
    """A throwaway pgvector Postgres on a random local port, removed afterwards."""
    if not shutil.which("podman"):
        pytest.skip("podman not available")
    port = free_port()
    name = f"kestrel-pgvector-test-{port}"
    run = subprocess.run(["podman", "run", "-d", "--rm", "--name", name, "-p", f"127.0.0.1:{port}:5432",
                          "-e", "POSTGRES_PASSWORD=lab", "-e", "POSTGRES_DB=kestrel", IMAGE],
                         capture_output=True, text=True)
    if run.returncode:
        pytest.skip(f"cannot start {IMAGE}: {run.stderr.strip()}")
    env = {"PGHOST": "127.0.0.1", "PGPORT": str(port), "PGUSER": "postgres",
           "PGPASSWORD": "lab", "PGDATABASE": "kestrel"}
    try:
        for _ in range(60):
            ready = subprocess.run(["podman", "exec", name, "pg_isready", "-U", "postgres", "-d", "kestrel"],
                                   capture_output=True)
            if ready.returncode == 0:
                time.sleep(1)   # the entrypoint restarts postgres once after init
                break
            time.sleep(1)
        yield env
    finally:
        subprocess.run(["podman", "rm", "-f", name], capture_output=True)


@pytest.fixture
def ingested(pg, work):
    work.apply_solution("module-05")
    out = work.run("ingest_corpus.py", env=pg).stdout
    assert "ingested" in out
    return pg


def search(work, env, *args):
    return json.loads(work.run("retrieval.py", *args, env=env).stdout)


def test_ingest_and_direct_search(work, ingested):
    assert "ingested 12 passages from 5 bulletins" in work.run("ingest_corpus.py", env=ingested).stdout  # re-runnable
    res = search(work, ingested, "coolant pump seal service interval")
    assert res["category"] == "ok" and res["data"]["passages"][0]["source"] == "SB-2024-117"
    assert "6,500" in res["data"]["passages"][0]["text"]
    assert search(work, ingested, "controller firmware delayed start")["data"]["passages"][0]["source"] == "SB-2024-140"


def test_out_of_corpus_queries_are_explicit_misses(work, ingested):
    # the K-900 does not exist: filtered by product, and also rejected by the score threshold alone
    res = work.run("-c", "import json, retrieval; print(json.dumps(["
                         "retrieval.search_bulletins('service interval', product='K-900'),"
                         "retrieval.search_bulletins('What is the service interval on a Kestrel K-900?'),"
                         "retrieval.search_bulletins('best pizza in Denver')]))", env=ingested).stdout
    cats = [r["category"] for r in json.loads(res)]
    assert cats == ["no_results", "no_results", "no_results"], cats


def test_unreachable_store_is_upstream_unavailable(work):
    work.apply_solution("module-05")
    res = json.loads(work.run("-c", "import json, retrieval; print(json.dumps(retrieval.search_bulletins('x')))",
                              env={"PGHOST": "127.0.0.1", "PGPORT": str(free_port())}).stdout)
    assert res["category"] == "upstream_unavailable" and res["retryable"] is True


def test_module5_invention_then_grounded_then_explicit_miss(work, ingested):
    work.repoint_to_validated()
    work.apply_solution("module-04")                       # no retrieval tool registered yet
    invented, _ = work.agent("m5", env=ingested)
    assert invented["tool_calls"] == [] and "8,000" in invented["answer"]      # confident invention
    work.apply_solution("module-05")                       # register the retrieval tool
    grounded, _ = work.agent("m5", env=ingested)
    call = grounded["tool_calls"][0]
    assert call["name"] == "search_bulletins" and call["result"]["category"] == "ok"
    assert call["result"]["data"]["passages"][0]["source"] == "SB-2024-117"
    assert "SB-2024-117" in grounded["answer"] and "6,500" in grounded["answer"]
    miss, _ = work.agent("m5-miss", env=ingested)
    assert miss["tool_calls"][0]["result"]["category"] == "no_results"
    assert "won't guess" in miss["answer"] and "3,000" not in miss["answer"]


@pytest.fixture
def gateway(work, ingested):
    # the gateway runs the tools server-side, so it needs the database settings, not the agent
    work.apply_solution("module-05")
    port = free_port()
    proc = spawn([sys.executable, str(HERE / "mock_gateway.py"), "--agent-dir", str(work.path),
                  "--port", str(port), "--prefix", "kestrel_"],
                 env={**work.env, **ingested})
    url = f"http://127.0.0.1:{port}/mcp"
    wait_for(f"http://127.0.0.1:{port}/x")
    yield port, url
    proc.terminate()


def register(port, tool):
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/_admin/register",
                                                  data=json.dumps({"tool": tool}).encode()))


def test_module6_gateway_is_behaviour_neutral_and_discovers_new_tool(work, ingested, gateway):
    port, url = gateway
    work.repoint_to_validated()
    local, _ = work.agent("m3", env=ingested)
    work.set_gateway(url)                                  # the only change: one gateway endpoint in config
    via_gw, run_dir = work.agent("m3", env=ingested)
    assert via_gw["ended_by"] == local["ended_by"] and via_gw["turns"] == local["turns"]
    assert [t["result"] for t in via_gw["tool_calls"]] == [t["result"] for t in local["tool_calls"]]
    assert via_gw["tool_calls"][0]["name"] == "kestrel_find_part"       # discovered, prefixed by the gateway
    offered = [t["function"]["name"] for t in read_json(run_dir / "01-request.json")["tools"]]
    assert "kestrel_estimate_delivery" not in offered

    before, _ = work.agent("m6", env=ingested)             # tool not registered: model has no tool to call
    assert before["tool_calls"] == []
    register(port, "estimate_delivery")                    # platform operation; agent files untouched
    after, _ = work.agent("m6", env=ingested)
    call = after["tool_calls"][0]
    assert call["name"] == "kestrel_estimate_delivery" and call["result"]["data"]["transit_days"] == 1
    assert "1 day" in after["answer"]


def test_module7_full_regression_against_assembled_agent(work, ingested, gateway):
    port, url = gateway
    work.repoint_to_validated()
    work.apply_solution("module-05")
    work.set_gateway(url)
    register(port, "estimate_delivery")
    out = work.run("regression.py", env=ingested).stdout
    assert "6 passed, 0 failed, 0 skipped" in out, out
    # and before module 5/6 the same command still reports per case without blocking
    work.config.write_text(work.config.read_text().replace(f'gateway_url = "{url}"', 'gateway_url = ""'))
    work.apply_solution("module-04")
    partial = work.run("regression.py", env=ingested).stdout
    assert "3 passed, 0 failed, 3 skipped" in partial, partial
