# Anti-Rationalization Reference

AI coding agents don't skip verification randomly. They rationalize it first. The rationalization follows predictable patterns.

---

## Hedging Language (Pre-Verification Skip)

| Phrase | What It Actually Means |
|---|---|
| "should work" | I haven't run it |
| "should be fine" | I haven't checked |
| "probably passes" | I haven't run the tests |
| "likely works" | I'm guessing based on code, not output |
| "seems to" | I'm reading code, not running it |
| "appears to" | Same |
| "as expected" | I expected it to work and didn't verify |
| "no issues" | I didn't look hard enough |

Rule: If you use any of these about a result, stop and run the verification command.

---

## Minimization Language (Pre-Process Skip)

| Phrase | What It Actually Means |
|---|---|
| "just a small change" | Small changes break things. Verify. |
| "trivial fix" | If trivial, verification takes 10 seconds. Do it. |
| "obvious improvement" | Prove it. |
| "minor update" | Pre-classifying risk to justify skipping checks |
| "quick cleanup" | Cleanup touches working code. Test it. |
| "simple refactor" | Refactors that break things are never called complex in advance |

Rule: The word "just" before a change description is a red flag.

---

## Completion Language (Pre-Report Without Evidence)

| Phrase | What It Actually Means |
|---|---|
| "essentially complete" | Not complete |
| "mostly done" | Not done |
| "everything is in place" | Something isn't |
| "all tests pass" | Show the output |
| "working as expected" | Show the evidence |
| "implementation complete" | Does the harness agree? |
| "matches the spec" | Quote the spec. Show the code. Show the match. |

Rule: Completion claims require evidence in the same message.

---

## Deferral Language (Acknowledging Without Acting)

| Phrase | What It Actually Means |
|---|---|
| "noted" | Will not change behavior |
| "good point" | Filing under things I'll do next time (won't) |
| "I'll keep that in mind" | Context window will forget in 3 messages |
| "understood" | Parsing complete. Behavior unchanged. |
| "will do" | Intention stated. Execution not guaranteed. |

Rule: Verbal acknowledgment does not change agent behavior. Only structural enforcement holds.

---

## Urgency Language (Pre-Bypass)

| Phrase | What It Actually Means |
|---|---|
| "to save time" | To skip verification |
| "given the urgency" | Using your deadline to justify bypass |
| "since this is time-sensitive" | Decided process doesn't apply under pressure |
| "let me just quickly..." | "Quickly" means "without verification" |

Rule: Urgency is exactly when process matters most.

---

## Self-Validation Language

| Phrase | What It Actually Means |
|---|---|
| "I've verified that..." | The builder verified the builder's work |
| "I confirmed..." | Same agent, same blind spots |
| "I checked and..." | Checking your own work doesn't count |
| "the logic is sound" | Static analysis by the model that wrote it |

Rule: The agent that wrote the code cannot be the sole verifier.

---

## The Principle

Agents rationalize by constructing plausible justification for the path of least resistance. The defense is naming the rationalization before it happens. When the rationalization is already in the agent's context as a known failure mode, the path of least resistance shifts from "skip and justify" to "verify and report."
