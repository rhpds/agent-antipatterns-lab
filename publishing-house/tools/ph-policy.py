#!/usr/bin/env python3
"""Fetch validation policy from Central API and write to ~/.config/publishing-house/policy.json.

Called at the start of every intake run so the skill always has fresh vocabulary data.
Overwrites any existing policy.json.
"""
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path


def main():
    auth_path = Path(os.path.expanduser("~/.config/publishing-house/auth.json"))
    if not auth_path.exists():
        print(json.dumps({"error": "~/.config/publishing-house/auth.json not found"}))
        sys.exit(1)

    creds = json.loads(auth_path.read_text())
    api_key = creds.get("credential", "")
    central_url = creds.get("central", "").rstrip("/")
    if not api_key or not central_url:
        print(json.dumps({"error": "Missing credential or central URL in auth.json"}))
        sys.exit(1)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = f"{central_url}/api/v1/spec/validation/policy"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            policy = json.loads(resp.read().decode())
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch policy: {e}"}))
        sys.exit(1)

    out_path = Path(os.path.expanduser("~/.config/publishing-house/policy.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(policy, indent=2))
    print(json.dumps({"ok": True, "path": str(out_path)}))


if __name__ == "__main__":
    main()
