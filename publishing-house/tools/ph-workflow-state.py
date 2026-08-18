#!/usr/bin/env python3
"""Query workflow stage by workflow_id. Read-only — writes nothing.

Usage: python ph-workflow-state.py <workflow_id>

Output: key:value pairs, one per line
  stage:intake
"""
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path


def main():
    if len(sys.argv) < 2 or not sys.argv[1]:
        print(json.dumps({"error": "Usage: ph-workflow-state.py <workflow_id>"}))
        sys.exit(1)

    wfid = sys.argv[1]

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

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            f"{central}/api/v1/projects/workflow-state/{wfid}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            st = json.loads(r.read().decode())
        stage = st.get("stage", "intake")
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch workflow state: {e}"}))
        sys.exit(1)

    print(f"stage:{stage}")


if __name__ == "__main__":
    main()
