#!/usr/bin/env python3
"""Post-session metrics dashboard. Run: python3 .anti-slop/harness/dashboard.py"""
import glob, json, os
from collections import Counter

REPORTS = ".anti-slop/reports"

def main():
    print("=" * 60)
    print("ANTI-SLOP SESSION METRICS")
    print("=" * 60)

    ev_path = os.path.join(REPORTS, "evidence.json")
    evidence, score = {}, 0
    if os.path.exists(ev_path):
        try:
            with open(ev_path) as f: evidence = json.load(f)
        except: print("\nevidence.json malformed")
        print(f"\nFiles changed:    {len(evidence.get('files_changed', []))}")
        print(f"Tests run:        {len(evidence.get('tests_run', []))}")
        print(f"API checks:       {len(evidence.get('api_checks', []))}")
        print(f"Browser checks:   {len(evidence.get('browser_checks', []))}")
        print(f"Commands total:   {len(evidence.get('commands_executed', []))}")
        if evidence.get("tests_run"): score += 40
        if evidence.get("api_checks"): score += 20
        if evidence.get("files_changed"): score += 20
        print(f"\nEvidence score:   {score}/80")
    else:
        print("\nNo evidence.json — session_init may not have run")

    fp = os.path.join(REPORTS, "incremental-findings.jsonl")
    if os.path.exists(fp):
        findings = []
        with open(fp) as f:
            for line in f:
                if line.strip():
                    try: findings.append(json.loads(line))
                    except: pass
        sev = Counter(f.get("severity", "?") for f in findings)
        cats = Counter(f.get("category", "?") for f in findings)
        pats = Counter(f.get("pattern", "?") for f in findings)
        print(f"\n--- FINDINGS ({len(findings)} total) ---")
        print("\nBy severity:")
        for s in ["critical", "high", "medium", "low"]:
            if sev.get(s): print(f"  {s:12s}  {sev[s]}")
        print("\nBy category:")
        for c, n in cats.most_common(): print(f"  {c:30s}  {n}")
        print("\nBy pattern:")
        for p, n in pats.most_common(10): print(f"  {p:30s}  {n}")
        ch = [f for f in findings if f.get("severity") in ("critical", "high")]
        score = max(0, score - 20) if ch else score + 20
        print(f"\nFinal evidence score: {score}/100")
    else:
        score += 20
        print(f"\nNo findings (clean session). Final score: {score}/100")

    rp = os.path.join(REPORTS, "anti-slop-report.json")
    if os.path.exists(rp):
        try:
            with open(rp) as f: report = json.load(f)
            mode = " (observe)" if report.get("observe_mode") else " (enforce)"
            print(f"\n--- STOP GATE ---\nDecision: {report.get('decision','?').upper()}{mode}")
            for fail in report.get("failures", [])[:5]: print(f"  - {fail[:120]}")
        except: pass

    sp = os.path.join(REPORTS, "sonnet-slop-check.json")
    if os.path.exists(sp):
        try:
            with open(sp) as f: sonnet = json.load(f)
            print(f"\n--- SONNET CHECK ---")
            print(f"Method:    {sonnet.get('method','?')}")
            print(f"Spec:      {'yes' if sonnet.get('spec_available') else 'no (universal only)'}")
            print(f"Criteria:  {sonnet.get('universal_criteria_count','?')} ({sonnet.get('learned_criteria_count',0)} learned)")
            sf = sonnet.get("findings", [])
            if sf:
                print(f"Findings ({len(sf)}):")
                for f in sf[:5]: print(f"  - [{f.get('severity','?')}] {f.get('detail','?')[:100]}")
            if sonnet.get("error"): print(f"Error: {sonnet['error']}")
        except: pass

    archives = sorted(glob.glob(os.path.join(REPORTS, "incremental-findings.jsonl.*")))
    if archives:
        print(f"\n--- TREND ({len(archives)} prior sessions) ---")
        for a in archives[-5:]:
            with open(a) as f: count = sum(1 for l in f if l.strip())
            print(f"  {a.split('.')[-1]}: {count} findings")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
