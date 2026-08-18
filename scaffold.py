#!/usr/bin/env python3
"""Set up this project for a specific lab pattern.

Requires Python 3.8+.  No external dependencies — stdlib only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

SCAFFOLD_DIR = Path(".scaffolds")
COMMON_DIR = SCAFFOLD_DIR / "common"
MANIFEST = Path("publishing-house/spec.yaml")

PATTERN_DIRS = [
    Path("runtime-automation"),
    Path("setup-automation"),
    Path("config"),
]

AUTOMATION_DIR = Path("automation")
AUTOMATION_SCAFFOLD_DIR = SCAFFOLD_DIR / "automation"

AUTOMATION_TYPES = ["ansible", "gitops", "both"]
TOPOLOGIES = ["shared-cluster", "per-student", "cnv-pool"]

PATTERNS: dict[str, tuple[str, str]] = {
    #  pattern-name   : (showroom_type, infrastructure)
    "agd-open":   ("classic", "agd_v2"),
    "agd-guided": ("guided",  "agd_v2"),
    "zt-guided":  ("guided",  "zt"),
}

MENU = """\
Which lab pattern?

  1. AgD v2 Open      — AgnosticD v2 infra, classic Showroom (no solve/validate)
  2. AgD v2 Guided    — AgnosticD v2 infra, guided Showroom (solve/validate buttons)
  3. ZT Guided        — Project Zero infra, guided Showroom (solve/validate buttons)
"""

MENU_MAP = {"1": "agd-open", "2": "agd-guided", "3": "zt-guided"}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the scaffold CLI."""
    parser = argparse.ArgumentParser(
        description="Set up this project for a specific lab pattern.",
    )
    parser.add_argument(
        "--pattern",
        choices=list(PATTERNS),
        help="Lab pattern to scaffold (skips interactive menu)",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompt on re-scaffold",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without touching the filesystem",
    )
    parser.add_argument(
        "--automation",
        choices=AUTOMATION_TYPES,
        default=None,
        help="Automation type to scaffold from `.scaffolds/automation/` into `automation/` "
             "(omit to skip automation scaffolding)",
    )
    parser.add_argument(
        "--topology",
        choices=TOPOLOGIES,
        default=None,
        help="Cluster topology — only affects gitops/both automation, where "
             "`shared-cluster` also copies bootstrap-tenant/",
    )
    return parser


def interactive_menu() -> str:
    """Present the interactive pattern selection menu."""
    print(MENU)
    while True:
        choice = input("Enter choice [1-3]: ").strip()
        if choice in MENU_MAP:
            return MENU_MAP[choice]
        print(f"Invalid choice: {choice!r}. Enter 1, 2, or 3.")


def update_manifest(path: Path, showroom_type: str, infrastructure: str) -> None:
    """Update showroom_type and infrastructure in the manifest YAML.

    Uses regex replacement to preserve comments and formatting.
    """
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'^(\s*showroom_type:\s*)""',
        rf'\g<1>"{showroom_type}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r'^(\s*infrastructure:\s*)""',
        rf'\g<1>"{infrastructure}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    path.write_text(text, encoding="utf-8")


def automation_copy_pairs(
    automation: str, topology: str | None
) -> list[tuple[Path, Path]]:
    """Resolve which `.scaffolds/automation/` subdirectories to copy for an automation type.

    Returns (source, dest) pairs — both relative to `.scaffolds/automation/` and `automation/`
    respectively; the layouts mirror each other (`gitops/bootstrap-infra/`,
    `gitops/bootstrap-tenant/`, `ansible/`).

    `bootstrap-tenant/` is only included when topology is `shared-cluster`. Topology is usually
    unknown at initial scaffold time — it's decided later during intake — so it's opt-in via
    `--topology` rather than inferred.
    """
    pairs: list[tuple[Path, Path]] = []
    if automation in ("ansible", "both"):
        pairs.append((Path("ansible"), Path("ansible")))
    if automation in ("gitops", "both"):
        pairs.append((Path("gitops/bootstrap-infra"), Path("gitops/bootstrap-infra")))
        if topology == "shared-cluster":
            pairs.append((Path("gitops/bootstrap-tenant"), Path("gitops/bootstrap-tenant")))
    return pairs


def scaffold(
    root: Path,
    pattern: str,
    *,
    force: bool,
    dry_run: bool,
    automation: str | None = None,
    topology: str | None = None,
) -> int:
    """Run the scaffolding process.  Returns 0 on success, 1 on error."""
    scaffold_dir = root / SCAFFOLD_DIR
    common_src = root / COMMON_DIR
    pattern_src = scaffold_dir / pattern
    manifest = root / MANIFEST

    # --- Pre-flight checks ---
    if not scaffold_dir.is_dir():
        print(
            "Error: This project has already been scaffolded. "
            f"The `{SCAFFOLD_DIR}/` directory was removed after initial scaffolding.",
            file=sys.stderr,
        )
        return 1

    if not (root / "publishing-house").is_dir():
        print(
            "Error: scaffold.py must be run from the template root — "
            f"expected to find `{SCAFFOLD_DIR}/` and `publishing-house/` in the current directory.",
            file=sys.stderr,
        )
        return 1

    if not pattern_src.is_dir():
        print(
            f"Error: Pattern {pattern!r} not found in `{SCAFFOLD_DIR}/`.",
            file=sys.stderr,
        )
        return 1

    showroom_type, infrastructure = PATTERNS[pattern]

    if topology and automation not in ("gitops", "both"):
        print(
            f"Warning: --topology {topology!r} has no effect without "
            "--automation gitops or --automation both (ignoring).",
            file=sys.stderr,
        )

    automation_src = root / AUTOMATION_SCAFFOLD_DIR
    automation_pairs: list[tuple[Path, Path]] = []
    if automation:
        automation_pairs = automation_copy_pairs(automation, topology)
        missing = [src for src, _dest in automation_pairs if not (automation_src / src).is_dir()]
        if missing:
            names = ", ".join(str(automation_src / m) for m in missing)
            print(f"Error: Automation source(s) not found: {names}.", file=sys.stderr)
            return 1

    # --- Check for existing pattern/automation dirs ---
    # Automation dirs are checked per top-level type (automation/ansible/, automation/gitops/)
    # rather than the whole automation/ tree, so re-running for one type doesn't clobber a
    # different type that's already in place.
    automation_top_dirs = sorted(
        {AUTOMATION_DIR / dest.parts[0] for _src, dest in automation_pairs}
    )
    dirs_to_check = list(PATTERN_DIRS) + automation_top_dirs
    existing = [d for d in dirs_to_check if (root / d).is_dir()]
    if existing and not force:
        if dry_run:
            print(f"Would remove existing directories: {', '.join(str(d) for d in existing)}")
        else:
            names = ", ".join(str(d) for d in existing)
            print(f"Existing pattern directories found: {names}")
            confirm = input("Re-scaffolding will clear and recreate them. Continue? [y/N] ").strip()
            if confirm.lower() not in ("y", "yes"):
                print("Aborted.")
                return 1

    # --- Dry-run summary ---
    if dry_run:
        print(f"\n--- Dry run: pattern={pattern} ---")
        if common_src.is_dir():
            common_files = sorted(
                p.relative_to(common_src)
                for p in common_src.rglob("*")
                if p.is_file()
            )
            print(f"  Copy from {common_src}/:")
            for f in common_files:
                print(f"    → {f}")
        files = sorted(
            p.relative_to(pattern_src)
            for p in pattern_src.rglob("*")
            if p.is_file()
        )
        print(f"  Copy from {pattern_src}/:")
        for f in files:
            print(f"    → {f}")
        if automation_pairs:
            print(f"  Copy from {automation_src}/:")
            for src, dest in automation_pairs:
                print(f"    {src} → {AUTOMATION_DIR / dest}")
        if manifest.is_file():
            print(
                f"  Update {manifest}: "
                f"showroom_type={showroom_type!r}, infrastructure={infrastructure!r}"
            )
        else:
            print(f"  Skip {manifest} update (file not present yet)")
        print(f"  Remove {scaffold_dir}/")
        print("No changes made.")
        return 0

    # --- Execute ---
    try:
        # 1. Remove any existing pattern-specific / automation directories
        for d in dirs_to_check:
            target = root / d
            if target.is_dir():
                shutil.rmtree(target)

        # 2. Copy common files (shared by every pattern) into project root
        if common_src.is_dir():
            shutil.copytree(common_src, root, dirs_exist_ok=True)

        # 3. Copy pattern-specific files into project root
        shutil.copytree(pattern_src, root, dirs_exist_ok=True)

        # 4. Copy automation files into automation/ (before .scaffolds/ is removed —
        #    this must happen in the same run since automation_type is known up front
        #    but topology usually isn't yet)
        for src, dest in automation_pairs:
            shutil.copytree(automation_src / src, root / AUTOMATION_DIR / dest, dirs_exist_ok=True)

        # 5. Update manifest (spec.yaml is populated by skeleton substitution;
        #    skip if it doesn't exist yet — fields will be set at instantiation)
        if manifest.is_file():
            update_manifest(manifest, showroom_type, infrastructure)

        # 6. Remove .scaffolds/
        shutil.rmtree(scaffold_dir)

    except OSError as exc:
        print(f"Error during scaffolding: {exc}", file=sys.stderr)
        print(
            "The project may be in a partial state. "
            "Re-run with --force to attempt recovery.",
            file=sys.stderr,
        )
        return 1

    # --- Summary ---
    print(f"\nScaffolded: {pattern}")
    print(f"  showroom_type:  {showroom_type}")
    print(f"  infrastructure: {infrastructure}")

    created = [d for d in PATTERN_DIRS if (root / d).is_dir()]
    if created:
        print(f"  created:        {', '.join(str(d) for d in created)}")
    if automation_pairs:
        automation_created = sorted(str(AUTOMATION_DIR / dest) for _src, dest in automation_pairs)
        print(f"  automation:     {', '.join(automation_created)}")
    print("\nNext: run /rhdp-publishing-house to start intake, or edit files directly.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point.  Parse args, resolve pattern, and run scaffold."""
    args = build_parser().parse_args(argv)

    root = Path.cwd()

    if args.pattern:
        pattern = args.pattern
    else:
        try:
            pattern = interactive_menu()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 1

    return scaffold(
        root,
        pattern,
        force=args.force,
        dry_run=args.dry_run,
        automation=args.automation,
        topology=args.topology,
    )


if __name__ == "__main__":
    raise SystemExit(main())
