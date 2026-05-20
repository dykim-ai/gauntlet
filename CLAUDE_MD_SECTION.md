## Anti-Slop Enforcement

This project uses an anti-slop harness that independently verifies your work
before you can complete a task.

### During work
- The harness scans every file you edit for slop patterns.
- If you see "ANTI-SLOP:" messages, address the issue before continuing.

### At completion
- The Stop hook checks: did you run tests? Are findings resolved? Any stubs remaining?
- If checks fail, you must fix them before stopping.
- "Done" means the harness agrees, not that you say so.

### Rules
- Do not write to .anti-slop/reports/ directly.
- Do not modify .anti-slop/harness/ scripts during a build session.
- Do not claim completion without running relevant tests.
