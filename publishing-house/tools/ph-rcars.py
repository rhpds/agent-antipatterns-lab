#!/usr/bin/env python3
"""RCARS advisor client. Submit a query, poll for results, or fetch catalog item details.

Usage:
  python ph-rcars.py submit "A beginner workshop covering OpenShift that teaches deployment"
  python ph-rcars.py poll <job_id>
  python ph-rcars.py catalog <ci_name>

Submit output:
  job_id:abc-123

Poll output:
  status:complete
  candidates:[{"display_name":"...","relevance_score":85,...}]

Catalog output:
  ci_name:LB1464
  is_agd_v2:True
  workloads:[{"workload_role":"...","workload_collection":"...","workload_fqcn":"..."}]
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
                    for c in candidates:
                        ci_name = c.get("ci_name", "")
                        if not ci_name:
                            continue
                        try:
                            cat_req = urllib.request.Request(
                                f"{central}/api/v1/rcars/catalog/{urllib.request.quote(ci_name)}",
                                headers=headers,
                            )
                            with urllib.request.urlopen(cat_req, context=ctx, timeout=15) as cr:
                                item = json.loads(cr.read().decode())
                            workloads = [
                                {"role": w["workload_role"], "collection": w["workload_collection"]}
                                for w in item.get("workloads", [])
                            ]
                            if workloads:
                                c["workloads"] = workloads
                        except Exception:
                            pass
                    print(f"status:{status}")
                    print(f"candidates:{json.dumps(candidates)}")
                    break
            except Exception as e:
                if time.monotonic() >= deadline:
                    print(f"status:error")
                    print(f"candidates:[]")
                    break
            time.sleep(10)

    elif action == "catalog":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: ph-rcars.py catalog <ci_name>"}))
            sys.exit(1)

        ci_name = sys.argv[2]
        try:
            req = urllib.request.Request(
                f"{central}/api/v1/rcars/catalog/{urllib.request.quote(ci_name)}",
                headers=headers,
            )
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                item = json.loads(r.read().decode())
            workloads = item.get("workloads", [])
            print(f"ci_name:{ci_name}")
            print(f"is_agd_v2:{item.get('is_agd_v2', False)}")
            print(f"workloads:{json.dumps(workloads)}")
        except Exception as e:
            print(f"ci_name:{ci_name}")
            print(f"is_agd_v2:false")
            print(f"workloads:[]")

    else:
        print(json.dumps({"error": f"Unknown action: {action}. Use 'submit', 'poll', or 'catalog'."}))
        sys.exit(1)


if __name__ == "__main__":
    main()
