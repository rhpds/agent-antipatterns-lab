"""Shared fixtures: mock endpoints, a throwaway copy of the agent, a pgvector container."""
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
AGENT = REPO / "agent"
HERE = pathlib.Path(__file__).parent
START_URL = "http://qwen3-8b-a-predictor.llm-serving.svc:8080/v1"   # the starting endpoint in config.toml


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(url, tries=50):
    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except urllib.error.HTTPError:
            return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"{url} did not come up")


def spawn(cmd, env=None):
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)


@pytest.fixture(scope="session")
def endpoints():
    """Two mock vLLM endpoints: the mismatched one the lab starts on, and the validated one."""
    procs, urls = [], {}
    for mode in ("mismatched", "validated"):
        port = free_port()
        procs.append(spawn([sys.executable, str(HERE / "mock_model.py"), "--mode", mode, "--port", str(port)]))
        urls[mode] = f"http://127.0.0.1:{port}/v1"
        wait_for(f"{urls[mode]}/models")
    yield urls
    for p in procs:
        p.terminate()


class Workdir:
    """A throwaway copy of agent/, standing in for a participant's workbench checkout."""

    def __init__(self, path, endpoints):
        self.path = path
        self.endpoints = endpoints
        self.env = {"PATH": "/usr/bin:/bin", "HOME": str(path)}
        self.config.write_text(self.config.read_text().replace(START_URL, endpoints["mismatched"]))

    @property
    def config(self):
        return self.path / "config.toml"

    def repoint_to_validated(self):
        """What module 2 asks the participant to do: edit the config file."""
        self.config.write_text(self.config.read_text().replace(self.endpoints["mismatched"], self.endpoints["validated"]))

    def apply_solution(self, module):
        for f in (AGENT / "solutions" / module).glob("*.py"):
            shutil.copy(f, self.path / f.name)

    def set_gateway(self, url):
        self.config.write_text(self.config.read_text().replace('gateway_url = ""', f'gateway_url = "{url}"'))

    def run(self, *args, env=None, check=True):
        out = subprocess.run([sys.executable, *args], cwd=self.path, capture_output=True, text=True,
                             env={**self.env, **(env or {})}, timeout=120)
        if check and out.returncode:
            raise AssertionError(f"{args} failed:\n{out.stdout}\n{out.stderr}")
        return out

    def agent(self, question, *extra, env=None):
        """Run agent.py on a named question and return (summary dict, run dir)."""
        runs = self.path / "runs"
        before = set(runs.glob("*")) if runs.exists() else set()
        self.run("agent.py", "--q", question, *extra, env=env)
        new = sorted(set(runs.glob("*")) - before)
        assert len(new) == 1
        return json.loads((new[0] / "summary.json").read_text()), new[0]


@pytest.fixture
def work(tmp_path, endpoints):
    dest = tmp_path / "agent"
    shutil.copytree(AGENT, dest, ignore=shutil.ignore_patterns("runs", "__pycache__", "solutions"))
    return Workdir(dest, endpoints)


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def fixture_part(name_contains, product):
    parts = read_json(AGENT / "fixtures" / "parts.json")["parts"]
    return next(p["part_number"] for p in parts if name_contains in p["name"].lower() and product in p["products"])
