# Governance Lifecycle: From Prose to Gate

A framework for evolving AI agent governance from documentation to structural enforcement.

---

## The Problem

Every team running AI coding agents starts the same way: they write rules in a markdown file. Then they discover the rules don't hold. The agent acknowledged them and violated them anyway.

The team rewrites the rules. Clearer. Bolder. More examples. The agent violates the rewritten rules too.

This is not a prompting problem. Prose rules are suggestions. Structural enforcement is physics.

---

## The Five Stages

### Stage 1: Prose

The rule exists as text in a markdown file.

Enforcement: None. The agent decides whether to follow it.

When sufficient: Low-stakes preferences like formatting and naming conventions.

### Stage 2: Prose + Audit

The rule exists as text AND someone checks after the fact.

Enforcement: Reactive. Violations detected but not prevented.

When sufficient: Rules where violation is detectable and reversible.

### Stage 3: Prose + Warning

A check runs in real-time and warns the agent.

Enforcement: Advisory. The agent can ignore the warning.

When sufficient: Calibration periods when tuning checks before enforcement.

### Stage 4: Gate

A structural mechanism the agent cannot bypass.

Enforcement: Preventive. No override, no rationalization.

Failure mode: The agent games the check (test theater, mock-only tests).

When sufficient: Most rules. Add checks for gaming patterns as they appear.

### Stage 5: Gate + Automated Recovery

The gate enforces the rule AND the system auto-recovers from circumvention attempts.

Enforcement: Self-healing. Bypass attempts detected and reversed.

When needed: Critical rules where failure cost is severe.

---

## The Escalation Principle

If an agent violates a prose rule more than twice, escalate to a gate. Don't rewrite the prose.

First violation: note it.
Second violation: note the pattern.
Third violation: build a gate.

Not: rewrite with more emphasis.
Not: add bold text and examples.

Prose teaches. Gates enforce. Don't ask prose to do enforcement's job.

---

## Applying to Claude Code

| Stage | Implementation |
|---|---|
| Prose | CLAUDE.md rules |
| Audit | PostToolUse hooks that log but don't block |
| Warning | Hooks that inject additionalContext warnings |
| Gate | Stop hook with exit code 2 |
| Recovery | Gate + session-start hook that restores state |

---

## Proportional Governance

Not every rule deserves Stage 5.

Code formatting: Stage 1. Doesn't matter enough to gate.
Running tests: Stage 4. Matters too much for warnings.
Production deployments: Stage 5. Cost of failure is severe.

The error is uniform governance. Match enforcement level to risk level.
