"""Put the agent back in the state a module starts from.

    python reset.py 4          # the starting state of module 4

Use it to recover from a broken edit, or to catch up with the room. Your current
versions of any changed files are copied to .reset-backup/<time>/ first, so nothing
you wrote is lost.

A module's starting state is the starter code, plus each earlier module's fix:
  module 2's repoint of config.toml to the validated endpoint (modules 3 and later),
  and solutions/module-NN for every earlier module that has one.
Module 6's gateway change has no supplied solution, so module 7 starts from module
6's starting state.
"""
import argparse
import datetime
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
# The endpoint the lab starts on, and the one module 2 repoints the agent to.
# The tests override these to point at their mock endpoints.
MISMATCHED = os.environ.get("LAB_MISMATCHED_URL", "http://qwen3-8b-a-predictor.llm-serving.svc:8080/v1")
VALIDATED = os.environ.get("LAB_VALIDATED_URL", "http://qwen3-8b-b-predictor.llm-serving.svc:8080/v1")
MODULES = range(1, 8)


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=True).stdout


def changed_files():
    """Tracked files under this directory that differ from the checked-out commit."""
    out = git("diff", "--name-only", "--relative", "HEAD", "--", ".")
    return [line for line in out.splitlines() if line]


def reset(module):
    changed = changed_files()
    backup = None
    if changed:
        backup = HERE / ".reset-backup" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        for name in changed:
            src = HERE / name
            if src.exists():
                (backup / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, backup / name)
        git("checkout", "HEAD", "--", *changed)

    steps = []
    if module >= 3:
        config = HERE / "config.toml"
        config.write_text(config.read_text().replace(MISMATCHED, VALIDATED))
        steps.append("config.toml points at the validated endpoint (module 2)")
    for earlier in range(3, module):
        solution = HERE / "solutions" / f"module-{earlier:02d}"
        if solution.is_dir():
            files = sorted(solution.glob("*.py"))
            for f in files:
                shutil.copy2(f, HERE / f.name)
            steps.append(f"module {earlier} fix applied ({', '.join(f.name for f in files)})")
    return changed, backup, steps


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reset the agent to the state a module starts from.")
    parser.add_argument("module", type=int, choices=MODULES, help="the module to start (1-7)")
    args = parser.parse_args(argv)
    try:
        changed, backup, steps = reset(args.module)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        sys.exit(f"reset needs the lab's git checkout: {getattr(exc, 'stderr', '') or exc}")
    print(f"Ready to start module {args.module}.")
    if backup:
        print(f"Your previous versions of {', '.join(changed)} are in {backup.relative_to(HERE)}/")
    for step in steps or ["starter code, unchanged"]:
        print(f"  - {step}")


if __name__ == "__main__":
    main()
