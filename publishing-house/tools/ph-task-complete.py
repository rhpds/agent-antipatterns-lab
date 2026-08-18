#!/usr/bin/env python3
"""Mark a development task as complete and close its Jira ticket.

Usage: python ph-task-complete.py <task_id>
  e.g. python ph-task-complete.py module-01
       python ph-task-complete.py write-automation
       python ph-task-complete.py write-e2e-tests
       python ph-task-complete.py write-health-check

Calls POST /jira/{epic_key}/task/{task_id}/complete

Output: JSON with {closed, ticket_key}
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
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: ph-task-complete.py <task_id>"}))
        sys.exit(1)

    task_id = sys.argv[1]

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
        epic_key = wd.get("epic_key", "")
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch workflow data: {e}"}))
        sys.exit(1)

    if not epic_key:
        print(json.dumps({"closed": False, "ticket_key": "", "detail": "No epic key — self-published mode"}))
        sys.exit(0)

    url = f"{central}/api/v1/jira/{epic_key}/task/{task_id}/complete"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            result = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            result = json.loads(body)
        except json.JSONDecodeError:
            result = {"error": body or e.reason}
    except Exception as e:
        result = {"error": f"Request failed: {e}"}

    print(json.dumps(result))

    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
