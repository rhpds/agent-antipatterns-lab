"""Modules 5 and 6: pgvector retrieval (throwaway podman container) and the full regression."""
import json
import shutil
import subprocess
import time

import pytest

from conftest import free_port

IMAGE = "docker.io/pgvector/pgvector:pg16"


@pytest.fixture(scope="session")
def pg():
    """A throwaway pgvector Postgres on a random local port, removed afterwards.

    If it can't start, the module 5 and 6 checks fail rather than skip: a skipped check reads as
    a pass, and these are the checks that exercise retrieval and the full regression.
    """
    if not shutil.which("podman"):
        pytest.fail("podman is not installed, so the bulletin database can't start: "
                    "the module 5 and 6 checks can't run. Install podman (they never skip).")
    port = free_port()
    name = f"kestrel-pgvector-test-{port}"
    run = subprocess.run(["podman", "run", "-d", "--rm", "--name", name, "-p", f"127.0.0.1:{port}:5432",
                          "-e", "POSTGRES_PASSWORD=lab", "-e", "POSTGRES_DB=kestrel", IMAGE],
                         capture_output=True, text=True)
    if run.returncode:
        pytest.fail(f"cannot start {IMAGE}, so the module 5 and 6 checks can't run: {run.stderr.strip()}")
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
    """Scenario: Without knowledge search, the agent invents a cause for fault F-21
    Scenario: With knowledge search, the F-21 answer follows the service bulletin
    Scenario: The agent says so when the bulletins have nothing"""
    work.repoint_to_validated()
    work.apply_solution("module-04")                       # no retrieval tool registered yet
    invented, _ = work.agent("m5", env=ingested)
    # As on the GPU (m5-start): the parts catalog has nothing on F-21, then a confident invention.
    [lookup] = invented["tool_calls"]
    assert lookup["name"] == "find_part" and lookup["arguments"] == {"query": "F-21", "product": "K-400"}
    assert lookup["result"]["category"] == "no_results" and "temperature sensor" in invented["answer"]
    work.apply_solution("module-05")                       # register the retrieval tool
    grounded, _ = work.agent("m5", env=ingested)
    call = grounded["tool_calls"][0]
    assert call["name"] == "search_bulletins" and call["result"]["category"] == "ok"
    assert "SB-2024-102" in {p["source"] for p in call["result"]["data"]["passages"]}
    assert "SB-2024-102" in grounded["answer"] and "coolant loop pressure low" in grounded["answer"]
    miss, _ = work.agent("m5-miss", env=ingested)
    assert miss["tool_calls"][0]["result"]["category"] == "no_results"
    assert "won't guess" in miss["answer"] and "3,000" not in miss["answer"]


def test_module6_full_regression_against_assembled_agent(work, ingested):
    """Scenario: The regression run checks every earlier case against the assembled agent"""
    work.repoint_to_validated()
    work.apply_solution("module-05")
    out = work.run("regression.py", env=ingested).stdout
    assert "5 passed, 0 failed, 0 skipped" in out, out
    # and before module 5 the same command still reports per case without blocking
    work.apply_solution("module-04")
    partial = work.run("regression.py", env=ingested).stdout
    assert "3 passed, 0 failed, 2 skipped" in partial, partial
