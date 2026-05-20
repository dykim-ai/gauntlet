#!/usr/bin/env python3
"""PostToolUse:Bash hook: collect evidence of test runs and commands."""
import json, os, re, sys

EVIDENCE_PATH = ".anti-slop/reports/evidence.json"
TEST_PATTERNS = [
    r"npm\s+test", r"npx\s+jest", r"npx\s+playwright", r"pytest",
    r"python.*-m\s+pytest", r"npx\s+vitest", r"mocha", r"npx\s+cypress",
    r"go\s+test", r"cargo\s+test", r"dotnet\s+test",
]

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)
    tool_input = event.get("tool_input", {})
    tool_response = event.get("tool_response", {})
    command = tool_input.get("command", "")
    stdout = tool_response.get("stdout", "") if isinstance(tool_response, dict) else str(tool_response)
    exit_code = tool_response.get("exit_code") if isinstance(tool_response, dict) else None
    if not os.path.exists(EVIDENCE_PATH):
        sys.exit(0)
    try:
        with open(EVIDENCE_PATH) as f:
            evidence = json.load(f)
    except Exception:
        sys.exit(0)
    evidence.setdefault("commands_executed", []).append({"command": command[:500], "exit_code": exit_code, "is_test": False})
    for pattern in TEST_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            evidence["commands_executed"][-1]["is_test"] = True
            evidence.setdefault("tests_run", []).append({
                "command": command[:200], "output_preview": stdout[:500],
                "passed": bool(re.search(r"(\d+)\s+pass", stdout, re.IGNORECASE)),
                "failed": bool(re.search(r"(\d+)\s+fail", stdout, re.IGNORECASE)),
            })
            break
    if re.search(r"curl\s+", command):
        evidence.setdefault("api_checks", []).append({"command": command[:200], "response_preview": stdout[:300]})
    if re.search(r"playwright|puppeteer|cypress", command, re.IGNORECASE):
        evidence.setdefault("browser_checks", []).append({"command": command[:200], "output_preview": stdout[:300]})
    with open(EVIDENCE_PATH, "w") as f:
        json.dump(evidence, f, indent=2)
    sys.exit(0)

if __name__ == "__main__":
    main()
