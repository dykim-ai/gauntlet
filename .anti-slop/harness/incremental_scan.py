#!/usr/bin/env python3
"""PostToolUse:Write|Edit|MultiEdit hook: incremental slop scan on changed file."""
import json, os, re, sys
from datetime import datetime, timezone

CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".sql", ".sh"}
REPORTS_DIR = ".anti-slop/reports"

# === CONFIGURE: internal terms that should never appear in UI strings ===
UI_LEAK_TERMS = []  # Add your project-specific terms here

def scan_file(file_path):
    try:
        with open(file_path, "r", errors="replace") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception:
        return []
    ext = os.path.splitext(file_path)[1].lower()
    findings = []
    is_test = "/test" in file_path or "/__test" in file_path or ".test." in file_path or ".spec." in file_path

    # 1. console.log in production
    if ext in {".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs"} and not is_test:
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("console.log(") and "// debug" not in s.lower():
                findings.append({"category": "code_quality", "severity": "medium", "file": file_path, "line": i, "pattern": "console_log", "detail": "console.log in production code", "text": s[:120]})

    # 2. TODO / FIXME / HACK / PLACEHOLDER
    for i, line in enumerate(lines, 1):
        for marker in ["TODO", "FIXME", "HACK", "XXX", "PLACEHOLDER"]:
            if marker in line.upper() and not line.strip().startswith("#!"):
                findings.append({"category": "fake_completeness", "severity": "high", "file": file_path, "line": i, "pattern": "todo_marker", "detail": f"{marker} marker", "text": line.strip()[:120]})
                break

    # 3. Commented-out code blocks (3+ lines)
    code_re = re.compile(r"(function|const |let |var |import |return |if\s*\(|for\s*\(|=\s*>|class |\{|\})")
    block_start, block_len = None, 0
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if (s.startswith("//") or s.startswith("#")) and code_re.search(s):
            if block_start is None: block_start = i
            block_len += 1
        else:
            if block_len >= 3:
                findings.append({"category": "code_quality", "severity": "medium", "file": file_path, "line": block_start, "pattern": "commented_out_code", "detail": f"{block_len} lines of commented-out code", "text": f"Lines {block_start}-{block_start+block_len-1}"})
            block_start, block_len = None, 0

    # 4. Mock/stub in non-test file
    if not is_test:
        for i, line in enumerate(lines, 1):
            if re.search(r"=\s*(mock|stub|fake)\(", line.strip(), re.IGNORECASE):
                findings.append({"category": "fake_completeness", "severity": "critical", "file": file_path, "line": i, "pattern": "mock_in_production", "detail": "Mock/stub in production code", "text": line.strip()[:120]})

    # 5. Not-implemented throws
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if re.search(r"throw new Error\(['\"]Not implemented", s, re.IGNORECASE) or "raise NotImplementedError" in s:
            findings.append({"category": "fake_completeness", "severity": "critical", "file": file_path, "line": i, "pattern": "not_implemented_throw", "detail": "Stub: not implemented", "text": s[:120]})

    # 6. Skipped tests
    if is_test:
        for i, line in enumerate(lines, 1):
            if re.search(r"\b(xit|xdescribe|xtest|@pytest\.mark\.skip|test\.skip)\b", line.strip()):
                findings.append({"category": "test_theater", "severity": "critical", "file": file_path, "line": i, "pattern": "skipped_test", "detail": "Skipped test", "text": line.strip()[:120]})

    # 7. Silent catches
    if ext in {".js", ".ts", ".tsx", ".jsx"}:
        for i, line in enumerate(lines, 1):
            if re.search(r"catch\s*\(.*\)\s*\{\s*\}", line.strip()):
                findings.append({"category": "fragile_glue", "severity": "high", "file": file_path, "line": i, "pattern": "silent_catch", "detail": "Empty catch block", "text": line.strip()[:120]})

    # 8. UI terminology leak (project-specific)
    if ext in {".tsx", ".jsx"} and UI_LEAK_TERMS:
        for i, line in enumerate(lines, 1):
            lower = line.lower()
            for term in UI_LEAK_TERMS:
                if term in lower and ('"' in line or "'" in line or "`" in line):
                    findings.append({"category": "product_mismatch", "severity": "high", "file": file_path, "line": i, "pattern": "ui_terminology_leak", "detail": f"Internal term '{term}' in UI", "text": line.strip()[:120]})

    # 9. Hardcoded secrets
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if re.search(r"(api_key|password|secret_key|PGPASSWORD)\s*=\s*['\"][^$\{]", s, re.IGNORECASE):
            if not s.startswith("#") and not s.startswith("//"):
                findings.append({"category": "security_privacy", "severity": "critical", "file": file_path, "line": i, "pattern": "hardcoded_secret", "detail": "Possible hardcoded credential", "text": s[:60]+"..."})

    return findings

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)
    tool_input = event.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path", "")
    if not file_path or not os.path.exists(file_path):
        sys.exit(0)
    if os.path.splitext(file_path)[1].lower() not in CODE_EXTENSIONS:
        sys.exit(0)
    findings = scan_file(file_path)
    if findings:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(os.path.join(REPORTS_DIR, "incremental-findings.jsonl"), "a") as f:
            for finding in findings:
                finding["timestamp"] = datetime.now(timezone.utc).isoformat()
                f.write(json.dumps(finding) + "\n")
        critical_high = [x for x in findings if x["severity"] in ("critical", "high")]
        if critical_high:
            summary = "; ".join(f"{f['pattern']} at {f['file']}:{f['line']}" for f in critical_high[:5])
            print(json.dumps({"additionalContext": f"ANTI-SLOP: {len(critical_high)} issue(s): {summary}. Address before completing."}))
    # Track file in evidence
    ev_path = os.path.join(REPORTS_DIR, "evidence.json")
    if os.path.exists(ev_path):
        try:
            with open(ev_path) as f:
                ev = json.load(f)
            if file_path not in ev.get("files_changed", []):
                ev.setdefault("files_changed", []).append(file_path)
                with open(ev_path, "w") as f:
                    json.dump(ev, f, indent=2)
        except Exception:
            pass
    sys.exit(0)

if __name__ == "__main__":
    main()
