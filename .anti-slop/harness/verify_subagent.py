#!/usr/bin/env python3
"""SubagentStop hook: verify subagent produced meaningful output."""
import json, sys

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)
    tool_response = event.get("tool_response", {})
    output_text = ""
    if isinstance(tool_response, dict):
        output_text = tool_response.get("text", "") or tool_response.get("result", "")
    elif isinstance(tool_response, str):
        output_text = tool_response
    if len(output_text.strip()) < 50:
        print(json.dumps({"additionalContext":
            f"ANTI-SLOP WARNING: Subagent output is {len(output_text.strip())} chars. "
            f"Verify it completed its task before reporting completion."}))
    sys.exit(0)

if __name__ == "__main__":
    main()
