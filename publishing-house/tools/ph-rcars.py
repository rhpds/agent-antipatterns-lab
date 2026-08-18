#!/usr/bin/env python3
"""RCARS advisor client. Submit a query or poll for results.

Usage:
  python ph-rcars.py submit "A beginner workshop covering OpenShift that teaches deployment"
  python ph-rcars.py poll <job_id>

Submit output:
  job_id:abc-123

Poll output:
  status:complete
  candidates:[{"display_name":"...","relevance_score":85,...}]
"""
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path


def load_auth():
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

    return api_key, central


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: ph-rcars.py submit <query> | poll <job_id>"}))
        sys.exit(1)

    action = sys.argv[1]
    api_key, central = load_auth()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {"Authorization": f"Bearer {api_key}"}

    if action == "submit":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: ph-rcars.py submit <query>"}))
            sys.exit(1)

        query = sys.argv[2]
        encoded = urllib.request.quote(query)
        try:
            req = urllib.request.Request(
                f"{central}/api/v1/rcars/advisor?query={encoded}",
                method="POST",
                headers=headers,
            )
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                result = json.loads(r.read().decode())
            job_id = result.get("job_id", "")
            print(f"job_id:{job_id}")
        except Exception as e:
            print(f"job_id:")
            sys.exit(0)

    elif action == "poll":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: ph-rcars.py poll <job_id>"}))
            sys.exit(1)

        import time

        job_id = sys.argv[2]
        deadline = time.monotonic() + 120
        while True:
            try:
                req = urllib.request.Request(
                    f"{central}/api/v1/rcars/advisor/{job_id}",
                    headers=headers,
                )
                with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                    result = json.loads(r.read().decode())
                status = result.get("status", "unknown")
                if status not in ("pending", "running") or time.monotonic() >= deadline:
                    candidates = result.get("result", {}).get("candidates", [])
                    print(f"status:{status}")
                    print(f"candidates:{json.dumps(candidates)}")
                    break
            except Exception as e:
                if time.monotonic() >= deadline:
                    print(f"status:error")
                    print(f"candidates:[]")
                    break
            time.sleep(10)

    else:
        print(json.dumps({"error": f"Unknown action: {action}. Use 'submit' or 'poll'."}))
        sys.exit(1)


if __name__ == "__main__":
    main()
