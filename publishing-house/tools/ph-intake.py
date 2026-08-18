#!/usr/bin/env python3
"""Submit intake to Central API — single call that validates and advances workflow.

POST /projects/intake/{slug} with {"repo_url": ..., "branch": ...}

Central API validates the spec server-side, then advances the workflow if validation passes.

Unified response shape for all outcomes:
  {"status": <int>, "stage": <str|null>, "error": <str|null>, "validation": <dict|null>}
"""
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

GITHUB_OAUTH_CLIENT_ID = "Ov23liWfLB2TbghERyPg"


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


def _load_auth():
    auth_path = Path(os.path.expanduser("~/.config/publishing-house/auth.json"))
    if not auth_path.exists():
        return None, auth_path
    return json.loads(auth_path.read_text()), auth_path


def _save_auth(data, auth_path):
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_path.write_text(json.dumps(data, indent=2))


def _github_user_from_token(token):
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()).get("login", "")
    except Exception:
        return ""


def _resolve_github_user_credential():
    """Try git credential fill to get a GitHub token, then resolve username."""
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return ""
        token = ""
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                token = line[len("password="):]
                break
        if not token:
            return ""
        return _github_user_from_token(token)
    except Exception:
        return ""


def _resolve_github_user_device_flow():
    """GitHub OAuth Device Flow — prompts user to authorize in browser."""
    try:
        req = urllib.request.Request(
            "https://github.com/login/device/code",
            data=urllib.parse.urlencode({
                "client_id": GITHUB_OAUTH_CLIENT_ID,
                "scope": "read:user",
            }).encode(),
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())

        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_uri = data["verification_uri"]
        interval = data.get("interval", 5)
        expires_in = data.get("expires_in", 900)

        print(f"\n  To authenticate with GitHub, open: {verification_uri}", file=sys.stderr)
        print(f"  Enter code: {user_code}\n", file=sys.stderr)

        deadline = time.time() + expires_in
        while time.time() < deadline:
            time.sleep(interval)
            req = urllib.request.Request(
                "https://github.com/login/oauth/access_token",
                data=urllib.parse.urlencode({
                    "client_id": GITHUB_OAUTH_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                }).encode(),
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                token_data = json.loads(r.read().decode())

            error = token_data.get("error", "")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval = token_data.get("interval", interval + 5)
                continue
            if error:
                print(f"  Device flow error: {error}", file=sys.stderr)
                return ""

            access_token = token_data.get("access_token", "")
            if access_token:
                return _github_user_from_token(access_token)

        print("  Device flow timed out.", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"  Device flow failed: {e}", file=sys.stderr)
        return ""


def resolve_github_user(creds, auth_path):
    """Three-tier GitHub username resolution: auth.json → git credential → device flow."""
    cached = creds.get("github_user", "")
    if cached:
        return cached

    username = _resolve_github_user_credential()
    if username:
        creds["github_user"] = username
        _save_auth(creds, auth_path)
        return username

    username = _resolve_github_user_device_flow()
    if username:
        creds["github_user"] = username
        _save_auth(creds, auth_path)
        return username

    return ""


def main():
    root = find_repo_root()
    if not root:
        print(json.dumps({"error": "catalog-info.yaml not found — not a Publishing House project"}))
        sys.exit(1)

    spec_path = root / "publishing-house" / "spec.yaml"
    if not spec_path.exists():
        print(json.dumps({"error": "publishing-house/spec.yaml not found"}))
        sys.exit(1)

    spec = yaml.safe_load(spec_path.read_text()) or {}
    project_id = spec.get("project", {}).get("slug", "")
    if not project_id:
        print(json.dumps({"error": "project.slug missing in spec.yaml"}))
        sys.exit(1)

    repo_url = get_repo_url(root)
    if not repo_url:
        print(json.dumps({"error": "Could not determine repo URL from catalog-info.yaml"}))
        sys.exit(1)

    creds, auth_path = _load_auth()
    if not creds:
        print(json.dumps({"error": "~/.config/publishing-house/auth.json not found — run the orchestrator skill first"}))
        sys.exit(1)

    api_key = creds.get("credential", "")
    if not api_key:
        print(json.dumps({"error": "No credential in auth.json"}))
        sys.exit(1)

    central_url = creds.get("central", "").rstrip("/")
    if not central_url:
        print(json.dumps({"error": "No portal URL in auth.json"}))
        sys.exit(1)

    github_user = resolve_github_user(creds, auth_path)
    if not github_user:
        print(json.dumps({"error": "Could not resolve GitHub username. Intake cannot proceed."}))
        sys.exit(1)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-GitHub-User": github_user,
    }

    intake_url = f"{central_url}/api/v1/projects/intake/{project_id}"
    intake_body = json.dumps({"repo_url": repo_url, "branch": "main"}).encode()
    req = urllib.request.Request(intake_url, data=intake_body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        result = json.loads(e.read().decode())
    except Exception as e:
        result = {"status": 500, "error": f"Request failed: {e}"}

    print(json.dumps(result))

    if result.get("status", 500) >= 400:
        sys.exit(1)


if __name__ == "__main__":
    main()
