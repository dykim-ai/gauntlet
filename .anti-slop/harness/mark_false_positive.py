#!/usr/bin/env python3
"""Mark a pattern as a false positive.
Usage: python3 .anti-slop/harness/mark_false_positive.py <pattern> [reason]"""
import json, os, sys

FP_PATH = ".anti-slop/policies/false-positives.json"

def main():
    if len(sys.argv) < 2:
        print("Usage: mark_false_positive.py <pattern_name> [reason]")
        fp = ".anti-slop/reports/incremental-findings.jsonl"
        if os.path.exists(fp):
            patterns = set()
            with open(fp) as f:
                for line in f:
                    if line.strip():
                        try: patterns.add(json.loads(line).get("pattern", "?"))
                        except: pass
            if patterns: print("\nRecent patterns:\n  " + "\n  ".join(sorted(patterns)))
        sys.exit(1)

    pattern, reason = sys.argv[1], " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    data = {}
    if os.path.exists(FP_PATH):
        try:
            with open(FP_PATH) as f: data = json.load(f)
        except: pass
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    if pattern in data:
        data[pattern]["count"] = data[pattern].get("count", 0) + 1
        if reason: data[pattern]["reason"] = reason
    else:
        data[pattern] = {"count": 1, "reason": reason}
    print(f"Marked '{pattern}' as false positive (count: {data[pattern]['count']})")
    if data[pattern]["count"] >= 3:
        print("  → Will be demoted by pattern_monitor on next run.")
    with open(FP_PATH, "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    main()
