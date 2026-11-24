#!/usr/bin/env python3
"""Fail before provisioning if a selected Git revision lacks the deployable lab.

Uses Git's own object lookup; never checks out or executes the selected release.
Fetch the configured origin first when checking a newly published branch/tag.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "automation/gitops/bootstrap-infra/Chart.yaml",
    "automation/gitops/bootstrap-infra/values.yaml",
    "automation/gitops/bootstrap-tenant/Chart.yaml",
    "automation/gitops/bootstrap-tenant/values.yaml",
    "agent/agent.py", "agent/requirements.txt", "notebooks/labnb.py",
]


def resolve(ref):
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("selected revision is required")
    for candidate in (ref, "origin/" + ref):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--end-of-options", candidate + "^{commit}"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    raise ValueError("selected revision is unavailable; fetch origin and verify the ref")


def check_release(ref):
    commit = resolve(ref)
    paths = set(subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", commit], cwd=ROOT, text=True,
    ).splitlines())
    missing = [path for path in REQUIRED if path not in paths]
    for number in range(1, 8):
        if not any(p.startswith(f"notebooks/module-{number:02d}-") and p.endswith(".ipynb") for p in paths):
            missing.append(f"notebooks/module-{number:02d}-*.ipynb")
    if missing:
        raise ValueError(f"missing required lab content at {commit[:12]}:\n  " + "\n  ".join(missing))
    return commit


def check_applications(document):
    import yaml

    def values_map(content):
        try:
            values = yaml.safe_load(content) or {}
        except yaml.YAMLError:
            raise ValueError("invalid Helm values; details withheld to protect credentials") from None
        if not isinstance(values, dict):
            raise ValueError("invalid Helm values; expected a mapping")
        return values

    commits = set()
    for app in document.get("items", [document]):
        source = app.get("spec", {}).get("source", {})
        if source.get("repoURL", "").removesuffix(".git") != "https://github.com/rhpds/agent-antipatterns-lab":
            continue
        path = source.get("path", "")
        if path not in ("automation/gitops/bootstrap-infra", "automation/gitops/bootstrap-tenant"):
            continue
        commit = check_release(source.get("targetRevision", ""))
        settings = source.get("helm", {})
        runtime_ref = None
        for value_file in ["values.yaml", *settings.get("valueFiles", [])]:
            content = subprocess.run(["git", "show", f"{commit}:{path}/{value_file}"],
                                     cwd=ROOT, capture_output=True, text=True)
            if content.returncode:
                raise ValueError("selected chart values file is unavailable")
            values = values_map(content.stdout)
            runtime_ref = values.get("labRepoRef", runtime_ref)
        # Never echo Helm values: RHDP includes participant passwords here.
        for values in (values_map(settings.get("values", "")), settings.get("valuesObject", {})):
            runtime_ref = values.get("labRepoRef", runtime_ref)
        for parameter in settings.get("parameters", []):
            if parameter.get("name") == "labRepoRef":
                runtime_ref = parameter.get("value")
        if not isinstance(runtime_ref, str) or not runtime_ref.strip():
            raise ValueError("labRepoRef is required for each lab Application")
        # origin/HEAD is a symbolic remote default, not a branch clone --branch can use.
        if runtime_ref == "HEAD" or not any(subprocess.run(["git", "show-ref", "--verify", "--quiet", prefix + runtime_ref],
                                  cwd=ROOT).returncode == 0
                   for prefix in ("refs/heads/", "refs/remotes/origin/", "refs/tags/")):
            raise ValueError("labRepoRef must be a fetched branch or tag usable by git clone --branch")
        try:
            runtime_commit = resolve(runtime_ref)
        except ValueError:
            raise ValueError("labRepoRef is unavailable; fetch origin and verify the runtime ref") from None
        if runtime_commit != commit:
            raise ValueError("labRepoRef and chart targetRevision select different releases")
        commits.add(commit)
    if not commits:
        raise ValueError("no lab Applications were found")
    if len(commits) != 1:
        raise ValueError("lab Applications select different releases")
    return commits.pop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", nargs="?", help="Selected branch, tag or chart commit, e.g. origin/test")
    parser.add_argument("--applications", metavar="FILE", help="Audit oc get applications JSON; - reads stdin (requires PyYAML)")
    args = parser.parse_args()
    if bool(args.ref) == bool(args.applications):
        parser.error("supply a ref or --applications FILE")
    try:
        if args.applications:
            content = sys.stdin.read() if args.applications == "-" else Path(args.applications).read_text()
            commit = check_applications(json.loads(content))
        else:
            commit = check_release(args.ref)
    except (ValueError, OSError):
        # Parsing errors can contain secret inline values; report those generically.
        # Our own validation messages contain only static text and Git paths.
        error = sys.exc_info()[1]
        message = str(error) if type(error) is ValueError else "unable to read the selected input"
        if isinstance(error, json.JSONDecodeError):
            message = "invalid Application JSON"
        print("FAIL: " + message, file=sys.stderr)
        return 1
    print(f"Lab release {commit[:12]} contains both charts, the agent and all seven notebooks; selected refs agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
