#!/usr/bin/env python3
"""PreToolUse:Bash hook: block dangerous commands before execution."""
import json, sys, re

# === CONFIGURE FOR YOUR PROJECT ===
BLOCKED = [
    (r"rm\s+-rf\s+/", "Recursive delete from root"),
    (r"DROP\s+(TABLE|DATABASE)", "SQL DROP statement"),
    (r"PGPASSWORD=", "Inline DB credentials"),
    (r"chmod\s+777", "World-writable permissions"),
    (r">\s*/dev/sd", "Direct disk write"),
    (r"mkfs\.", "Filesystem format"),
]
WARNED = [
    (r"git\s+push.*-f", "Force push — verify branch"),
    (r"npm\s+publish", "Publishing to npm — verify scope"),
    (r"migration.*run|migrate", "Migration — verify target DB"),
]

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)
    command = event.get("tool_input", {}).get("command", "")
    for pattern, reason in BLOCKED:
        if re.search(pattern, command, re.IGNORECASE):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": f"BLOCKED: {reason}"}}))
            sys.exit(0)
    for pattern, reason in WARNED:
        if re.search(pattern, command, re.IGNORECASE):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": f"WARNING: {reason}"}}))
            sys.exit(0)
    sys.exit(0)

if __name__ == "__main__":
    main()
