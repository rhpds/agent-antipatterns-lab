"""Put the agent back in the state a module starts from.

    python reset.py 4          # the starting state of module 4

Use it to recover from a broken edit, or to catch up with the room. Your own edits
are copied to .reset-backup/<time>/ first, so nothing you wrote is lost. Files that
only hold what the lab supplied (a solution, or module 2's repoint) aren't copied.

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
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
# The endpoint the lab starts on, and the one module 2 repoints the agent to.
# The tests override these to point at their mock endpoints.
MISMATCHED = os.environ.get("LAB_MISMATCHED_URL", "http://qwen3-8b-a-predictor.llm-serving.svc:8080/v1")
VALIDATED = os.environ.get("LAB_VALIDATED_URL", "http://qwen3-8b-b-predictor.llm-serving.svc:8080/v1")
MODULES = range(1, 8)


def git(*args):
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=True).stdout


def changed_files(*diff_filter):
    """Tracked files under this directory that differ from the checked-out commit."""
    out = git("diff", "--name-only", "--relative", *diff_filter, "HEAD", "--", ".")
    return [line for line in out.splitlines() if line]


def supplied_copies(name):
    """Contents the lab itself puts in `name`: a supplied solution, or module 2's repoint."""
    copies = [f.read_bytes() for f in (HERE / "solutions").glob(f"module-*/{name}")]
    if name == "config.toml":
        copies.append(git("show", "HEAD:./config.toml").replace(MISMATCHED, VALIDATED).encode())
    return copies


class NotAFile(Exception):
    """A tracked file's path holds something else, such as a directory."""


def reset(module):
    # Restoring would replace whatever is there without a backup, so stop instead.
    odd = [name for name in changed_files()
           if os.path.lexists(HERE / name) and not (HERE / name).is_file()]
    if odd:
        raise NotAFile(f"{', '.join(odd)} should be a file but isn't; move it aside and run reset again")
    # Back up only the participant's own edits. A file that holds exactly what an earlier
    # reset (or the module's instructions) put there is lab-supplied, and backing it up
    # on every reset would bury real edits under copies of the solutions. A deleted file
    # has nothing to back up; it is restored below.
    changed = [name for name in changed_files()
               if (HERE / name).is_file()
               and (HERE / name).read_bytes() not in supplied_copies(name)]
    restore = changed_files("--diff-filter=a")
    backup = None
    if changed:
        # A new directory per run, so two resets in the same second never share one and the
        # second can't overwrite the first's copies of the participant's edits.
        root = HERE / ".reset-backup"
        root.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = pathlib.Path(tempfile.mkdtemp(prefix=f"{stamp}-", dir=root))
        for name in changed:
            (backup / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HERE / name, backup / name)
    # Restore everything except files the participant added: those have no version at
    # HEAD to restore (git checkout would reject them), so they stay, backed up as well.
    if restore:
        git("checkout", "HEAD", "--", *restore)

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
    except NotAFile as exc:
        sys.exit(f"reset stopped, nothing changed: {exc}")
    print(f"Ready to start module {args.module}.")
    if backup:
        print(f"Your previous versions of {', '.join(changed)} are in {backup.relative_to(HERE)}/")
    for step in steps or ["starter code, unchanged"]:
        print(f"  - {step}")


if __name__ == "__main__":
    main()
