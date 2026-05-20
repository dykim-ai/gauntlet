# Gauntlet

**A self-improving quality gate that prevents AI coding agents from shipping unverifiable code.**

AI coding agents have a consistent failure mode: they produce code that *looks complete but isn't*. Stubbed functions behind TODO markers. Tests that only assert mocks. Features that return hardcoded values. Migrations that exist as files but were never applied. The agent says "done" and the human trusts it because the output is long and confident.

These aren't bugs — they're **slop**.

Gauntlet is a deterministic enforcement layer for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that independently verifies an agent's work before it can stop. The agent cannot declare "done" by prose — it must satisfy mechanical checks, semantic evaluation by a separate model, and learned rules that get stricter over time.

No external services, databases, or orchestration infrastructure required. Pure Python + Claude Code hooks.

---

## How It Works

### Three Verification Layers

| Layer | What Runs | What It Catches | Cost |
|---|---|---|---|
| **Mechanical** | Python scripts (regex, file checks) | console.logs, TODOs, mocks in production, stubs, commented-out code, empty catch blocks, hardcoded secrets, skipped tests | $0, <100ms |
| **Semantic** | Claude Code Sonnet subagent | Hardcoded returns where computation expected, test theater (tests that only assert mocks), dead code, API contract mismatches, migration/code drift | ~$0.01-0.03/session |
| **Learned** | Pattern monitor (offline) | Auto-promoted rules from recurring findings across sessions — the harness gets stricter over time | $0 |

### The Enforcement Loop

The agent writes code. PostToolUse hooks scan every file edit and log findings. When the agent tries to stop, the Stop hook runs mechanical checks (did tests run, are findings resolved, are there stubs) and spawns a Sonnet subagent with isolated context to evaluate the diff against 10 universal acceptance criteria. If all checks pass, the agent may stop. If any check fails, the hook exits with code 2, Claude Code re-injects the failure reason as a prompt, and the agent must continue working.

The coding agent is **never** in its own verification chain. Deterministic scripts and a separate Sonnet model invocation verify its work independently.

### The Self-Improving Loop

1. Every finding is logged with timestamps, categories, and severity
2. Session archives accumulate over time
3. The **pattern monitor** analyzes findings across sessions
4. Pattern in **3+ sessions** — auto-promoted to learned rule (medium)
5. Pattern in **5+ sessions** — escalated to high
6. Pattern in **8+ sessions** — escalated to critical
7. Marked as false positive **3+ times** — demoted or removed

The harness gets smarter without manual rule authoring.

---

## Slop Taxonomy

Preloaded patterns from real-world AI agent failure modes:

| Category | What It Catches | Severity |
|---|---|---|
| **Fake completeness** | TODOs, stubs, mocks in production, hardcoded returns, exit signals without output artifacts | Critical |
| **Test theater** | Tests that assert mocks only, skipped tests, no tests despite code changes | Critical |
| **Architecture drift** | SQL injection vectors, LLM calls where deterministic code expected, migration/code mismatches | Critical |
| **Fragile glue** | Empty catch blocks, retry without idempotency | High |
| **Code quality** | console.logs, commented-out code, magic numbers | Medium |
| **Security** | Hardcoded credentials, secrets in logs | Critical |

### Universal Acceptance Criteria

Ten criteria evaluated by Sonnet against every diff, no per-task authoring required:

1. Every new function has a clear purpose and is called or tested
2. Functions named compute, calculate, score actually compute (not hardcoded)
3. Tests import and execute real implementation (not just mocks)
4. Error handling does something meaningful (not empty catches)
5. No dead code added (unreachable functions, unused imports)
6. API response shapes match what callers expect
7. Migration column names match service code
8. No unrelated scope creep
9. Commit description matches what the diff implements
10. Shared code changes have regression tests

---

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Python 3.10+

### Step 1: Clone

    git clone https://github.com/dykim-ai/gauntlet.git /tmp/gauntlet

### Step 2: Copy into your project

    cd ~
    cp -r /tmp/gauntlet/.anti-slop .
    mkdir -p .claude
    cp /tmp/gauntlet/.claude/settings.local.json .claude/settings.local.json
    chmod +x .anti-slop/harness/*.py
    rm -rf /tmp/gauntlet

If you already have .claude/settings.local.json with hooks, merge the entries instead of overwriting.

### Step 3: Add to CLAUDE.md

Append the contents of CLAUDE_MD_SECTION.md to your project CLAUDE.md.

### Step 4: Gitignore reports

    echo ".anti-slop/reports/" >> .gitignore

### Step 5: Start Claude Code

    claude

Verify hooks fired:

    cat .anti-slop/reports/evidence.json

Should show session_start timestamp. Everything is automated. No manual approvals.

---

## Monitoring

### Dashboard

Run after every session:

    python3 .anti-slop/harness/dashboard.py

Shows files changed, tests run, findings by severity/category/pattern, stop gate verdict, Sonnet check results, and trend across prior sessions.

### Report Files

| File | Contents | Updated |
|---|---|---|
| evidence.json | Files changed, tests run, commands | Throughout session |
| incremental-findings.jsonl | Every finding with file, line, severity | On each file edit |
| anti-slop-report.json | Stop gate verdict | When agent tries to stop |
| sonnet-slop-check.json | Sonnet evaluation results | When agent tries to stop |

### Learning Loop

Run after several sessions:

    python3 .anti-slop/harness/pattern_monitor.py

Analyzes findings across all sessions and auto-promotes recurring patterns to permanent rules.

### False Positives

    python3 .anti-slop/harness/mark_false_positive.py magic_number "HTTP status codes are fine"

Three marks demotes the pattern on next monitor run.

---

## Configuration

### Observe Mode to Enforcement

Ships in observe mode (warn only). Switch to enforcement after tuning:

    sed -i 's/OBSERVE_MODE = True/OBSERVE_MODE = False/' .anti-slop/harness/stop_gate.py
    sed -i 's/OBSERVE_MODE = True/OBSERVE_MODE = False/' .anti-slop/harness/sonnet_slop_check.py

### Blocked Commands

Add project-specific patterns to pre_bash_gate.py BLOCKED list.

### UI Terminology Leaks

Add internal terms to incremental_scan.py UI_LEAK_TERMS list.

### Project-Specific Slop Patterns

Add patterns to slop-taxonomy.yaml under project_specific section.

### Task-Specific Specs (Optional)

For critical tasks, create TASK_SPEC.md in project root. Sonnet checks it alongside universal criteria.

---

## Architecture

The system hooks into Claude Code at six lifecycle points: SessionStart (reset state, inject taxonomy), PreToolUse:Bash (block dangerous commands), PostToolUse:Write/Edit (scan each edit), PostToolUse:Bash (log test runs), Stop (mechanical gate + Sonnet subagent), and SubagentStop (verify subagent output).

### File Structure

    .claude/settings.local.json         Hooks configuration
    .anti-slop/harness/
      session_init.py                    SessionStart hook
      pre_bash_gate.py                   PreToolUse:Bash hook
      incremental_scan.py               PostToolUse:Write|Edit hook
      collect_evidence.py                PostToolUse:Bash hook
      stop_gate.py                       Stop hook (mechanical)
      sonnet_slop_check.py              Stop hook (Sonnet subagent)
      universal_spec.py                  10 universal acceptance criteria
      verify_subagent.py                 SubagentStop hook
      pattern_monitor.py                 Learning loop
      mark_false_positive.py             False positive management
      dashboard.py                       Post-session metrics
    .anti-slop/policies/
      slop-taxonomy.yaml                 Pattern definitions
      learned-rules.json                 Auto-generated by monitor
      false-positives.json               Marked false positives
    .anti-slop/reports/                  Runtime artifacts (gitignored)

---

## How This Differs From Linters

A linter checks syntax. Gauntlet checks whether the agent **actually did what it claims**.

A linter flags a missing return type. Gauntlet flags that computeRiskScore returns a hardcoded 0.75.

A linter finds an unused import. Gauntlet finds that npm test passed but the tests only assert mock return values.

A linter runs once. Gauntlet learns — patterns that recur across sessions get auto-promoted with escalating severity.

---

## Contributing

If you encounter a new AI agent failure mode:

1. Document it with pattern ID, category, severity, detection method
2. Add to slop-taxonomy.yaml
3. If mechanical: add detection to incremental_scan.py
4. If semantic: add criterion to universal_spec.py
5. Submit a PR

Real-world failure examples are especially valuable.

---

## License

GNU Affero General Public License v3.0 — see LICENSE
