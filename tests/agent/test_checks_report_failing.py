"""A check that can't run must fail, never skip or pass."""
import os
import subprocess
import sys

import pytest

from conftest import HERE

# The tests that need the pgvector container (modules 5, 6 and 7).
NEEDS_BULLETIN_DB = ["-k", "test_module5 or test_module6 or test_module7"]


def run_checks(tmp_path, fake_podman=None):
    """Run the module 5-7 tests in a child pytest on a machine with no usable podman."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if fake_podman:
        podman = bin_dir / "podman"
        podman.write_text(fake_podman)
        podman.chmod(0o755)
    env = {"PATH": str(bin_dir), "HOME": str(tmp_path), "PYTHONPATH": os.pathsep.join(sys.path)}
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs",
                           str(HERE / "test_knowledge_and_gateway.py"), *NEEDS_BULLETIN_DB],
                          cwd=HERE, env=env, capture_output=True, text=True, timeout=120)


def assert_reported_failing(out, why):
    summary = out.stdout.strip().splitlines()[-1]
    assert out.returncode != 0, out.stdout
    assert "3 error" in summary or "3 failed" in summary, out.stdout       # module 5, 6 and 7
    assert "skipped" not in summary and "passed" not in summary, out.stdout
    assert why in out.stdout, out.stdout                                    # and it says why


def test_missing_podman_fails_the_module_5_to_7_checks(tmp_path):
    """Scenario: A check that can't run is reported as failing, not passing"""
    assert_reported_failing(run_checks(tmp_path), "podman is not installed")


@pytest.mark.skipif(os.name == "nt", reason="the stand-in podman is a shell script")
def test_a_bulletin_database_that_cannot_start_fails_the_module_5_to_7_checks(tmp_path):
    """Scenario: A check that can't run is reported as failing, not passing
    (the clause: podman is there, but the database image won't start)"""
    out = run_checks(tmp_path, fake_podman="#!/bin/sh\necho 'image not found' >&2\nexit 125\n")
    assert_reported_failing(out, "cannot start")
