#!/usr/bin/env python3
"""SessionStart hook: initialize anti-slop state for this session."""
import json, os, sys
from datetime import datetime, timezone

REPORTS_DIR = ".anti-slop/reports"

def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    findings_path = os.path.join(REPORTS_DIR, "incremental-findings.jsonl")
    if os.path.exists(findings_path):
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        os.rename(findings_path, f"{findings_path}.{ts}")

    evidence = {
        "session_start": datetime.now(timezone.utc).isoformat(),
        "tests_run": [], "commands_executed": [], "files_changed": [],
        "api_checks": [], "browser_checks": [],
    }
    with open(os.path.join(REPORTS_DIR, "evidence.json"), "w") as f:
        json.dump(evidence, f, indent=2)

    context_parts = []
    taxonomy_path = ".anti-slop/policies/slop-taxonomy.yaml"
    if os.path.exists(taxonomy_path):
        with open(taxonomy_path) as f:
            context_parts.append("SLOP TAXONOMY (active):\n" + "".join(f.readlines()[:80]))

    if os.path.exists("TASK_SPEC.md"):
        with open("TASK_SPEC.md") as f:
            context_parts.append(f"TASK SPEC:\n{f.read()[:2000]}")

    output = {"additionalContext": "\n---\n".join(context_parts)} if context_parts else {}
    print(json.dumps(output))

if __name__ == "__main__":
    main()
