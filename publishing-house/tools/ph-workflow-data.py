#!/usr/bin/env python3
"""Query workflow data for a project. Read-only — writes nothing.

Calls /workflow-data with the project slug to resolve workflow_id and epic_key.

Output: key:value pairs, one per line
  workflow_id:abc-123
  epic_key:RHDPCD-456
"""
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

import yaml


def find_repo_root():
    p = Path.cwd()
    while p != p.parent:
        if (p / "catalog-info.yaml").exists():
            return p
        p = p.parent
    return None


def main():
    root = find_repo_root()
    if not root:
        print(json.dumps({"error": "catalog-info.yaml not found"}))
        sys.exit(1)

    auth_path = Path(os.path.expanduser("~/.config/publishing-house/auth.json"))
    if not auth_path.exists():
        print(json.dumps({"error": "~/.config/publishing-house/auth.json not found"}))
        sys.exit(1)

    creds = json.loads(auth_path.read_text())
    api_key = creds.get("credential", "")
    central = creds.get("central", "").rstrip("/")
    if not api_key or not central:
        print(json.dumps({"error": "Missing credential or central in auth.json"}))
        sys.exit(1)

    spec_path = root / "publishing-house" / "spec.yaml"
    spec = yaml.safe_load(spec_path.read_text()) or {} if spec_path.exists() else {}
    project = spec.get("project", {})

    project_id = project.get("slug", "")
    if not project_id:
        print(json.dumps({"error": "project.slug missing in spec.yaml"}))
        sys.exit(1)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            f"{central}/api/v1/projects/{project_id}/workflow-data",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            wd = json.loads(r.read().decode())
        wfid = wd.get("workflow_id", "")
        epic_key = wd.get("epic_key", "")
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch workflow data: {e}"}))
        sys.exit(1)

    print(f"workflow_id:{wfid}")
    print(f"epic_key:{epic_key}")


if __name__ == "__main__":
    main()
