#!/usr/bin/env python3
"""Run live pytest acceptance and always write a module review report.

Set LB8000_KUBECONFIG, LB8000_PARTICIPANTS (two comma-separated usernames)
and LB8000_RELEASE (the exact deployed commit). Outputs contain no credentials.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--readiness-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"status": "FAIL", "scope": "readiness" if args.readiness_only else "e2e",
              "reason": "", "commit": os.environ.get("LB8000_RELEASE", ""),
              "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "modules": [{"module": n, "status": "INCOMPLETE", "evidence": [],
                           "issues": ["Live module checks have not completed"]} for n in range(1, 8)]}
    required = ("LB8000_KUBECONFIG", "LB8000_PARTICIPANTS", "LB8000_RELEASE")
    missing = [key for key in required if not os.environ.get(key)]
    participants = os.environ.get("LB8000_PARTICIPANTS", "").split(",")
    if missing:
        report["reason"] = "Missing required configuration: " + ", ".join(missing)
    elif (len(set(participants)) != 2 or
          any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,57}[a-z0-9])?", p) for p in participants)):
        report["reason"] = "Exactly two different participant usernames are required"
    elif not re.fullmatch(r"[0-9a-f]{40}", report["commit"]):
        report["reason"] = "LB8000_RELEASE must be the full tested commit SHA"
    else:
        # Never reuse an earlier run's passing XML when a later invocation cannot run.
        junit = args.output.resolve() / f"junit-{uuid.uuid4().hex}.xml"
        report["junit"] = junit.name
        command = [sys.executable, "-m", "pytest", str(ROOT / "tests/e2e"), "-q", "-rA",
                   "-o", "junit_family=xunit1", "--junitxml", str(junit), "--basetemp", str(args.output.resolve() / "pytest")]
        if args.readiness_only:
            command += ["-k", "readiness"]
        done = subprocess.run(command, cwd=ROOT, env={**os.environ, "LB8000_EVIDENCE_DIR": str(args.output.resolve())})
        cases = []
        if junit.exists():
            for case in ET.parse(junit).iter("testcase"):
                failure = next((child for child in case if child.tag in ("error", "failure", "skipped")), None)
                cases.append({"name": case.attrib.get("name", ""),
                              "status": "PASS" if failure is None else "FAIL",
                              "reason": "" if failure is None else failure.attrib.get("message", "Check did not pass")})
                for prop in case.findall("properties/property"):
                    if prop.attrib.get("name") == "runtime":
                        cases[-1]["runtime"] = json.loads(prop.attrib["value"])
        readiness = [case for case in cases if "readiness" in case["name"]]
        ready = len(readiness) == 2 and all(c["status"] == "PASS" for c in readiness)
        docs = [case for case in cases if "each_module_is_ready_for_david_to_review" in case["name"]]
        docs_ready = len(docs) == 1 and docs[0]["status"] == "PASS"
        for row in report["modules"]:
            matching = [case for case in cases if f"module-{row['module']:02d}" in case["name"]]
            row["evidence"] = matching
            row["issues"] = [c["reason"] for c in matching if c["status"] != "PASS"]
            if ready and docs_ready and len(matching) == 2 and all(c["status"] == "PASS" for c in matching):
                row["status"] = "PASS"
            else:
                row["issues"] += ["Required readiness, documentation or two-participant module evidence is incomplete"]
        if done.returncode == 0 and cases and (args.readiness_only or all(r["status"] == "PASS" for r in report["modules"])):
            report["status"] = "PASS"
        report["reason"] = "Readiness only; module verification incomplete" if args.readiness_only else "See individual checks and junit.xml"
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Lab module review", "", f"Result: {report['status']}",
             f"Tested commit: {report['commit'] or 'not selected'}", "", report["reason"], "",
             "| Module | Notebook | Showroom preview | Live checks | Execution evidence | Unresolved issues |",
             "|---|---|---|---|---|---|"]
    for row, notebook in zip(report["modules"], sorted((ROOT / "notebooks").glob("module-*.ipynb"))):
        source = f"https://github.com/rhpds/agent-antipatterns-lab/blob/{report['commit']}/{notebook.relative_to(ROOT)}" if report["commit"] else str(notebook)
        page = ROOT / "www/modules" / notebook.with_suffix(".html").name
        issues = "; ".join(row["issues"]).replace("|", "\\|").replace("\n", " ")
        artifacts = ", ".join(f"[Participant {i+1}]({case['runtime']['artifact']})" for i, case in enumerate(row["evidence"])
                              if case.get("runtime", {}).get("artifact"))
        lines.append(f"| {row['module']} | [Notebook]({source}) | [Rendered page]({page}) | {row['status']} | {artifacts} | {issues} |")
    lines += ["", f"Evidence: [structured report](report.json), [individual live checks]({report.get('junit', 'not-run')}).",
              "The Showroom links refer to the local preview build. Live results do not establish publication."]
    (args.output / "review.md").write_text("\n".join(lines) + "\n")
    print(f"{report['status']}: {args.output / 'review.md'}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
