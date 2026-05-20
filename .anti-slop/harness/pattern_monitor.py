#!/usr/bin/env python3
"""Pattern Monitor — auto-promotes recurring findings to permanent rules.
Run after sessions: python3 .anti-slop/harness/pattern_monitor.py"""
import glob, json, os
from collections import Counter, defaultdict
from datetime import datetime, timezone

REPORTS_DIR = ".anti-slop/reports"
LEARNED_RULES_PATH = ".anti-slop/policies/learned-rules.json"
FALSE_POSITIVES_PATH = ".anti-slop/policies/false-positives.json"
PROMOTE_MEDIUM, PROMOTE_HIGH, PROMOTE_CRITICAL = 3, 5, 8
FP_DEMOTE = 3

def load_all_findings():
    findings = []
    for path in [os.path.join(REPORTS_DIR, "incremental-findings.jsonl")] + glob.glob(os.path.join(REPORTS_DIR, "incremental-findings.jsonl.*")):
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if line.strip():
                        try: findings.append(json.loads(line))
                        except: pass
    return findings

def main():
    findings = load_all_findings()
    if not findings:
        print("No findings data yet. Run some sessions first.")
        return

    # Group by session (date+hour as proxy)
    sessions = defaultdict(list)
    for f in findings:
        sessions[f.get("timestamp", "")[:13]].append(f)
    print(f"Analyzed {len(findings)} findings across {len(sessions)} sessions.\n")

    # Count sessions per pattern
    fp = {}
    if os.path.exists(FALSE_POSITIVES_PATH):
        try:
            with open(FALSE_POSITIVES_PATH) as f: fp = json.load(f)
        except: pass
    fp = {k: v for k, v in fp.items() if not k.startswith("_")}

    pattern_sessions = defaultdict(set)
    pattern_examples = defaultdict(list)
    pattern_cats = defaultdict(str)
    for sk, sf in sessions.items():
        seen = set()
        for f in sf:
            p = f.get("pattern", "?")
            if p not in seen:
                pattern_sessions[p].add(sk)
                seen.add(p)
            pattern_examples[p].append(f)
            pattern_cats[p] = f.get("category", "code_quality")

    candidates = []
    for pattern, ss in sorted(pattern_sessions.items(), key=lambda x: -len(x[1])):
        count = len(ss)
        if fp.get(pattern, {}).get("count", 0) >= FP_DEMOTE: continue
        if count >= PROMOTE_CRITICAL: sev = "critical"
        elif count >= PROMOTE_HIGH: sev = "high"
        elif count >= PROMOTE_MEDIUM: sev = "medium"
        else: continue
        ex = pattern_examples[pattern][0] if pattern_examples[pattern] else {}
        candidates.append({
            "id": f"LC-{pattern[:20].upper().replace('_','-')}",
            "pattern": pattern, "category": pattern_cats[pattern],
            "severity": sev, "session_count": count,
            "total_occurrences": len(pattern_examples[pattern]),
            "question": f"Does this diff contain the pattern '{pattern}'? ({ex.get('detail', '')[:80]})",
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        })

    if not candidates:
        print(f"No patterns crossed threshold ({PROMOTE_MEDIUM}+ sessions).")
        return

    print(f"{'Pattern':<30} {'Sessions':>8} {'Severity':>10}")
    print("-" * 50)
    for c in candidates:
        print(f"{c['pattern']:<30} {c['session_count']:>8} {c['severity']:>10}")

    os.makedirs(os.path.dirname(LEARNED_RULES_PATH), exist_ok=True)
    with open(LEARNED_RULES_PATH, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "promoted_rules": candidates}, f, indent=2)
    print(f"\nWrote {len(candidates)} learned rules to {LEARNED_RULES_PATH}")

if __name__ == "__main__":
    main()
