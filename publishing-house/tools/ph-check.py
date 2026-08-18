#!/usr/bin/env python3
"""ph-check.py — Publishing House compliance checker.

Calls Central API's validate endpoint for server-side validation.
Falls back to a minimal offline message if Central is unreachable.

Usage:
  python publishing-house/tools/ph-check.py              # Run all checks
  python publishing-house/tools/ph-check.py --stage review  # Run review checks
  python publishing-house/tools/ph-check.py --verbose    # Show passing checks too
"""
import argparse
import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from pathlib import Path

import yaml


def find_repo_root():
    p = Path.cwd()
    while p != p.parent:
        if (p / "catalog-info.yaml").exists():
            return p
        p = p.parent
    return None


def get_repo_url(root):
    catalog_path = root / "catalog-info.yaml"
    catalog = yaml.safe_load(catalog_path.read_text())
    slug = catalog.get("metadata", {}).get("annotations", {}).get("github.com/project-slug", "")
    if slug:
        return f"https://github.com/{slug}"
    links = catalog.get("metadata", {}).get("links", [])
    for link in links:
        if link.get("title") == "Repository":
            return link.get("url", "")
    return ""


def main():
    parser = argparse.ArgumentParser(description="Publishing House compliance checker")
    parser.add_argument("--stage", default="intake", help="Validation stage (intake, review)")
    parser.add_argument("--verbose", action="store_true", help="Show passing checks too")
    args = parser.parse_args()

    root = find_repo_root()
    if not root:
        print("ERROR: Not a Publishing House project — catalog-info.yaml not found.", file=sys.stderr)
        sys.exit(2)

    spec_path = root / "publishing-house" / "spec.yaml"
    if not spec_path.exists():
        print("ERROR: publishing-house/spec.yaml not found.", file=sys.stderr)
        sys.exit(2)

    spec = yaml.safe_load(spec_path.read_text()) or {}
    project_id = spec.get("project", {}).get("slug", "")
    if not project_id:
        print("ERROR: project.slug missing in spec.yaml", file=sys.stderr)
        sys.exit(2)

    repo_url = get_repo_url(root)
    if not repo_url:
        print("ERROR: Could not determine repo URL from catalog-info.yaml", file=sys.stderr)
        sys.exit(2)

    auth_path = Path(os.path.expanduser("~/.config/publishing-house/auth.json"))
    if not auth_path.exists():
        print("ERROR: ~/.config/publishing-house/auth.json not found", file=sys.stderr)
        sys.exit(2)

    creds = json.loads(auth_path.read_text())
    api_key = creds.get("credential", "")
    central_url = creds.get("central", "").rstrip("/")
    if not api_key or not central_url:
        print("ERROR: Missing credential or central URL in auth.json", file=sys.stderr)
        sys.exit(2)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"{central_url}/api/v1/spec/validation/{project_id}?stage={args.stage}"
    body = json.dumps({"repo_url": repo_url, "branch": "main"}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode())
    except Exception as e:
        print(f"ERROR: Central API unreachable: {e}", file=sys.stderr)
        sys.exit(2)

    symbols = {"pass": "✅", "fail": "❌", "warn": "⚠️ ", "skip": "⏭️ "}
    passed = failed = warned = 0

    print(f"Project: {project_id} | Stage: {args.stage}")
    print()

    for r in data.get("results", []):
        st = r.get("status", "")
        sym = symbols.get(st, "  ")
        if st == "pass":
            passed += 1
            if args.verbose:
                print(f"{sym} [{r['check_id']}] {r['message']}")
        elif st == "fail":
            failed += 1
            print(f"{sym} [{r['check_id']}] {r['message']}")
            if r.get("field"):
                print(f"     Field: {r['field']}")
        elif st in ("warn", "skip"):
            warned += 1
            if args.verbose:
                print(f"{sym} [{r['check_id']}] {r['message']}")

    auto = data.get("auto_computed")
    if auto:
        print()
        print("Auto-computed:")
        if auto.get("peak_environments") is not None:
            print(f"  Peak environments: {auto['peak_environments']}")
        if auto.get("cost_per_run_est") is not None:
            print(f"  Cost estimate: ~${auto['cost_per_run_est']}/run")
        if auto.get("provisioning_time_min") is not None:
            print(f"  Provisioning time: ~{auto['provisioning_time_min']} min")

    print()
    print("─" * 50)
    total = passed + failed + warned
    print(f"Results: {passed} passed, {failed} failed, {warned} skipped/warned")
    if failed > 0:
        print("❌ Compliance check FAILED")
        sys.exit(1)
    elif warned > 0:
        print("⚠️  Compliance check PASSED with warnings")
        sys.exit(0)
    else:
        print("✅ All checks PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
