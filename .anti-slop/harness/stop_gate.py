#!/usr/bin/env python3
"""Stop hook: verify the agent produced sufficient evidence before allowing completion.
Exit 0 = agent may stop. Exit 2 = agent must continue (stderr re-injected as prompt).
"""
import json, os, sys
from datetime import datetime, timezone

# === CONFIGURATION ===
OBSERVE_MODE = True  # True = warn only, False = enforcement
# === END CONFIGURATION ===

REPORTS_DIR = ".anti-slop/reports"
EVIDENCE_PATH = os.path.join(REPORTS_DIR, "evidence.json")
FINDINGS_PATH = os.path.join(REPORTS_DIR, "incremental-findings.jsonl")

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        event = {}
    failures = []
    evidence = {}

    # Check 1: Evidence exists and has substance
    if not os.path.exists(EVIDENCE_PATH):
        failures.append("No evidence.json found. Run tests and verify your changes before completing.")
    else:
        try:
            with open(EVIDENCE_PATH) as f:
                evidence = json.load(f)
        except Exception as e:
            failures.append(f"evidence.json malformed: {e}")
            evidence = {}
        files_changed = evidence.get("files_changed", [])
        if files_changed:
            tests_run = evidence.get("tests_run", [])
            if not tests_run:
                fl = ", ".join(files_changed[:10])
                failures.append(f"Changed {len(files_changed)} file(s) but ran zero tests. Changed: {fl}")
            failed = [t for t in tests_run if t.get("failed")]
            if failed:
                failures.append(f"{len(failed)} test run(s) had failures. Fix before completing.")

    # Check 2: No unresolved critical/high findings
    if os.path.exists(FINDINGS_PATH):
        critical_high = []
        try:
            with open(FINDINGS_PATH) as f:
                for line in f:
                    if not line.strip(): continue
                    finding = json.loads(line)
                    if finding.get("severity") in ("critical", "high"):
                        if os.path.exists(finding.get("file", "")):
                            critical_high.append(finding)
        except Exception:
            pass
        if critical_high:
            summary = "\n".join(f"  - [{f['severity'].upper()}] {f['pattern']}: {f['detail']} ({f['file']}:{f.get('line','?')})" for f in critical_high[:10])
            failures.append(f"{len(critical_high)} unresolved critical/high finding(s):\n{summary}")

    # Check 3: No stubs in changed files
    for fpath in evidence.get("files_changed", []):
        if not os.path.exists(fpath): continue
        try:
            with open(fpath, "r", errors="replace") as f:
                content = f.read()
            if "throw new Error('Not implemented')" in content or 'throw new Error("Not implemented")' in content:
                failures.append(f"{fpath} contains 'Not implemented' stub.")
            if "# todo: implement" in content.lower() or "// todo: implement" in content.lower():
                failures.append(f"{fpath} contains 'TODO: implement'.")
            if "raise NotImplementedError" in content and "class " not in content:
                failures.append(f"{fpath} contains NotImplementedError stub.")
        except Exception:
            pass

    # Write report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": "fail" if failures else "pass",
        "observe_mode": OBSERVE_MODE,
        "failures": failures,
        "files_changed": evidence.get("files_changed", []),
        "tests_run": len(evidence.get("tests_run", [])),
    }
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(os.path.join(REPORTS_DIR, "anti-slop-report.json"), "w") as f:
        json.dump(report, f, indent=2)

    if failures:
        if OBSERVE_MODE:
            print(json.dumps({"additionalContext": "ANTI-SLOP ADVISORY (observe mode): " + "; ".join(failures[:3])}))
            sys.exit(0)
        else:
            print("\n".join(failures), file=sys.stderr)
            sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
