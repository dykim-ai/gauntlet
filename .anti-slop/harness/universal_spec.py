#!/usr/bin/env python3
"""Universal Acceptance Spec — criteria that apply to EVERY code change without per-task authoring."""

UNIVERSAL_CRITERIA = [
    {"id": "UC-001", "name": "function_purpose", "severity": "high", "category": "fake_completeness",
     "question": "Does every new or modified function have a clear purpose exercised by at least one caller or test? Flag functions that exist but are never called and never tested."},
    {"id": "UC-002", "name": "real_computation", "severity": "critical", "category": "fake_completeness",
     "question": "Does every function that implies computation by its name (score, calculate, compute, analyze, evaluate, predict, estimate, rank, classify, extract, parse, transform, validate, generate) actually perform that computation? Flag any that return hardcoded values, constants, or placeholders."},
    {"id": "UC-003", "name": "test_exercises_real_code", "severity": "critical", "category": "test_theater",
     "question": "Do the test files import and execute the actual implementation? Flag tests that only assert mock return values, only verify functions were called (toHaveBeenCalled), or only use snapshot assertions without verifying behavior."},
    {"id": "UC-004", "name": "error_path_handled", "severity": "high", "category": "fragile_glue",
     "question": "For every new try/catch or error handling block, does the catch path do something meaningful (return error response, throw typed error, log and re-throw)? Flag empty catch blocks and catch blocks that only log without propagating."},
    {"id": "UC-005", "name": "no_dead_code_added", "severity": "medium", "category": "code_quality",
     "question": "Does the diff add any unreachable code? Functions never called, variables never read, imports never used, code after unconditional return/throw."},
    {"id": "UC-006", "name": "api_contract_consistency", "severity": "high", "category": "architecture_drift",
     "question": "If the diff modifies an API endpoint, does the response shape match what callers expect? Flag mismatched field names, types, or structures between backend response and frontend consumption."},
    {"id": "UC-007", "name": "migration_matches_code", "severity": "critical", "category": "architecture_drift",
     "question": "If the diff includes a database migration, do table/column names match what service or model code references? Flag mismatches."},
    {"id": "UC-008", "name": "no_scope_creep", "severity": "medium", "category": "code_quality",
     "question": "Does the diff contain files or changes unrelated to the primary purpose? Flag unrelated modifications."},
    {"id": "UC-009", "name": "description_matches_diff", "severity": "high", "category": "fake_completeness",
     "question": "If a commit message or task description is visible, does the diff actually implement what it claims? Flag cases where description says 'implement X' but diff only adds scaffolding or stubs."},
    {"id": "UC-010", "name": "no_regression_risk", "severity": "high", "category": "fragile_glue",
     "question": "Does the diff modify shared utilities, middleware, or base classes? If so, are there tests verifying existing behavior is preserved? Flag high-risk shared code changes without regression tests."},
]

def build_universal_prompt(diff, learned_criteria=None):
    """Build the Sonnet prompt using universal + learned criteria."""
    all_criteria = UNIVERSAL_CRITERIA + (learned_criteria or [])
    criteria_block = "\n".join(f"{i}. [{c['id']}] {c['question']}" for i, c in enumerate(all_criteria, 1))
    return f"""You are a code quality evaluator. Check this diff against each criterion.

CODE DIFF:
{diff}

CRITERIA:
{criteria_block}

Respond with ONLY a JSON object:
{{"results": [{{"id": "UC-001", "passed": true, "detail": ""}}], "findings": [{{"id": "UC-002", "severity": "critical", "category": "fake_completeness", "detail": "specific issue"}}], "test_theater_detected": false}}

No explanation, no markdown fences."""

def get_learned_criteria():
    """Load learned criteria from auto-promoted rules."""
    import os, json
    path = ".anti-slop/policies/learned-rules.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            rules = json.load(f)
        return [{"id": r["id"], "name": r["pattern"], "question": r["question"],
                 "severity": r["severity"], "category": r["category"], "source": "learned"}
                for r in rules.get("promoted_rules", [])]
    except Exception:
        return []
