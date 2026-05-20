#!/usr/bin/env python3
"""
Anti-Slop Semantic Checker — spawns a Claude Code Sonnet subagent.

Architecture:
  The main Claude Code agent runs on Opus. This script, called from the
  Stop hook, spawns a SEPARATE Claude process on Sonnet via the `claude`
  CLI. The Sonnet subagent evaluates the diff in isolated context — it
  never sees the builder agent's conversation or reasoning.

  Primary:  claude CLI (--model sonnet, one-shot mode)
  Fallback: direct Anthropic API call (if claude CLI unavailable)

This is criteria matching, not reasoning. Sonnet checks whether the
diff satisfies universal acceptance criteria and (optionally) a task spec.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === CONFIGURATION ===
OBSERVE_MODE = True
SONNET_MODEL = "claude-sonnet-4-6"
REPORTS_DIR = ".anti-slop/reports"
MAX_DIFF_LINES = 300
MAX_SPEC_LINES = 100
# === END CONFIGURATION ===


def get_diff():
    """Get the git diff for this session's work."""
    for cmd in [
        ["git", "diff", "--unified=3"],
        ["git", "diff", "--staged", "--unified=3"],
        ["git", "diff", "HEAD~1", "--unified=3"],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            diff = result.stdout.strip()
            if diff:
                lines = diff.split("\n")
                if len(lines) > MAX_DIFF_LINES:
                    diff = "\n".join(lines[:MAX_DIFF_LINES]) + f"\n... ({len(lines) - MAX_DIFF_LINES} lines truncated)"
                return diff
        except Exception:
            continue
    return ""


def get_task_spec():
    """Load optional TASK_SPEC.md."""
    for path in ["TASK_SPEC.md", ".anti-slop/current-task.md", "task.md"]:
        if os.path.exists(path):
            with open(path, "r", errors="replace") as f:
                lines = f.readlines()
            if len(lines) > MAX_SPEC_LINES:
                return "".join(lines[:MAX_SPEC_LINES]) + "\n... (truncated)"
            return "".join(lines)
    return ""


def get_test_files():
    """Get content of test files modified in this session."""
    try:
        result = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, timeout=10)
        changed = result.stdout.strip().split("\n")
        test_files = [f for f in changed if f and ("test" in f.lower() or "spec" in f.lower())]
        content = {}
        for tf in test_files[:3]:
            if os.path.exists(tf):
                with open(tf, "r", errors="replace") as f:
                    c = f.read()
                content[tf] = c[:3000] + "\n... (truncated)" if len(c) > 3000 else c
        return content
    except Exception:
        return {}


def build_prompt(diff, spec, test_content, learned_criteria):
    """Build the full evaluation prompt for the Sonnet subagent."""
    # Universal criteria
    try:
        from universal_spec import UNIVERSAL_CRITERIA
        all_criteria = UNIVERSAL_CRITERIA + (learned_criteria or [])
    except ImportError:
        all_criteria = learned_criteria or []

    criteria_block = ""
    for i, c in enumerate(all_criteria, 1):
        criteria_block += f"{i}. [{c['id']}] {c['question']}\n"

    sections = [f"CODE DIFF:\n{diff}"]

    if spec:
        sections.append(f"TASK SPECIFICATION (check in addition to universal criteria):\n{spec}")

    if test_content:
        tests_summary = "\n\n".join(f"FILE: {name}\n{content}" for name, content in test_content.items())
        sections.append(f"TEST FILES:\n{tests_summary}")

    content = "\n\n".join(sections)

    return f"""You are a code quality evaluator. Check this diff against each criterion. For each, answer true (satisfied) or false (violation found).

{content}

UNIVERSAL CRITERIA:
{criteria_block}

{"TASK-SPECIFIC: Also check each acceptance criterion in the task specification above." if spec else ""}

{"TEST QUALITY: Also check whether the test files exercise real code or only assert mocks." if test_content else ""}

Respond with ONLY a JSON object:
{{
  "results": [
    {{"id": "UC-001", "passed": true, "detail": ""}},
    {{"id": "UC-002", "passed": false, "detail": "function computeScore returns hardcoded 0.75"}}
  ],
  "findings": [
    {{"id": "UC-002", "severity": "critical", "category": "fake_completeness", "detail": "computeScore returns hardcoded 0.75 instead of computing"}}
  ],
  "test_theater_detected": false
}}

No explanation, no markdown fences. ONLY the JSON object."""


def call_via_claude_cli(prompt):
    """Primary: spawn a Claude Code Sonnet subagent via the claude CLI."""
    try:
        result = subprocess.run(
            ["claude", "--model", SONNET_MODEL, "-p", prompt],
            capture_output=True, text=True, timeout=40,
            env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "hook"}
        )
        text = result.stdout.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)
    except FileNotFoundError:
        return None  # claude CLI not available — fall back
    except json.JSONDecodeError:
        return {"findings": [], "error": "Could not parse Sonnet response as JSON"}
    except subprocess.TimeoutExpired:
        return {"findings": [], "error": "Sonnet subagent timed out"}
    except Exception as e:
        return {"findings": [], "error": str(e)}


def call_via_api(prompt):
    """Fallback: direct Anthropic API call (requires ANTHROPIC_API_KEY)."""
    import urllib.request
    import urllib.error

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"findings": [], "error": "No claude CLI and no ANTHROPIC_API_KEY"}

    payload = {
        "model": SONNET_MODEL,
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        return {"findings": [], "error": str(e)}


def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        event = {}

    diff = get_diff()
    if not diff:
        sys.exit(0)

    # Load learned criteria
    learned = []
    try:
        from universal_spec import get_learned_criteria
        learned = get_learned_criteria()
    except ImportError:
        pass

    spec = get_task_spec()
    test_files = get_test_files()
    prompt = build_prompt(diff, spec, test_files, learned)

    # Try claude CLI first (subagent), fall back to API
    result = call_via_claude_cli(prompt)
    method = "claude_cli"
    if result is None:
        result = call_via_api(prompt)
        method = "api_fallback"

    findings = result.get("findings", [])

    # Write report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": SONNET_MODEL,
        "method": method,
        "observe_mode": OBSERVE_MODE,
        "findings": findings,
        "diff_lines": len(diff.split("\n")),
        "spec_available": bool(spec),
        "universal_criteria_count": 10 + len(learned),
        "learned_criteria_count": len(learned),
        "test_files_checked": list(test_files.keys()),
        "test_theater_detected": result.get("test_theater_detected", False),
        "error": result.get("error"),
    }
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(os.path.join(REPORTS_DIR, "sonnet-slop-check.json"), "w") as f:
        json.dump(report, f, indent=2)

    # Handle findings
    critical = [f for f in findings if f.get("severity") == "critical"]
    if critical:
        summary = "; ".join(f.get("detail", "")[:100] for f in critical[:3])
        if OBSERVE_MODE:
            print(json.dumps({"additionalContext":
                f"ANTI-SLOP (Sonnet, observe): {len(critical)} critical finding(s): {summary}"
            }))
            sys.exit(0)
        else:
            print(f"ANTI-SLOP (Sonnet): {len(critical)} critical finding(s): {summary}. Fix before completing.", file=sys.stderr)
            sys.exit(2)

    if findings:
        summary = "; ".join(f.get("detail", "")[:80] for f in findings[:3])
        print(json.dumps({"additionalContext": f"ANTI-SLOP (Sonnet): {len(findings)} finding(s): {summary}"}))

    sys.exit(0)

if __name__ == "__main__":
    main()
