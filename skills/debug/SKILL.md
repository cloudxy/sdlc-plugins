---
name: debug
description: "Use this skill when the spawn packet attaches debug_protocol or $debug. Do NOT use from parent /sdlc or for new features."
when_to_use: "Spawn packet carries debug_protocol, or $debug. Do NOT use from parent /sdlc or for anything other than locating a defect's mechanism."
---

# Debug — locate the mechanism, then fix the minimum

Procedure for **rework respawns** (round 2+ on the same hat). The producing hat keeps its identity and its primary procedure skill; this is the method it follows to stop the loop. Manager-side rules (when to attach, `root_cause` bookkeeping) live in the orchestrator's debug-loop reference (skills/sdlc/references/debug-loop) — do not read that file; your packet's `debug_protocol` field is your instruction to be here.

A repeated G-fresh fail is a **hypothesis problem, not an effort problem**. Re-running the same inputs and hoping is a bare retry — forbidden.

## The loop (in order, no skipping)

1. **Reproduce.** One command + exit code showing the failure verbatim (failed gate, failing test, rejected artifact diff). Cannot reproduce → say so and return what you tried; do not "fix" what you cannot see.
2. **Isolate.** Bisect the surface until the failure has one smallest trigger. Record each eliminated hypothesis as one line: `hypothesis → probe → result`.
3. **Root cause, one line.** Name the **mechanism** ("router imports ORM, transaction boundary lost", "GWT oracle contradicts FR-3"), never the symptom ("test fails"). If you cannot write the mechanism in one sentence, go back to step 2.
4. **Minimal fix.** Touch the smallest surface the mechanism implies. No drive-by refactors, no unrelated cleanup in a rework round — that is how round 3 starts.
5. **Re-run the failed gate.** The exact command from step 1. Paste verbatim output + exit code.
6. **Debug record.** Append to `T-<n>-evidence.md` under `## Debug record`: reproduce command, eliminated hypotheses, root cause line, fix summary, re-run output.
7. **Return** `root_cause: <the one line>` — the manager writes it into the gate record.

## Gotchas

- **The changelog is not the cause.** "Fixed X" in a prior round tells you what was tried, not why it failed. Re-derive from the artifact.
- **One mechanism per round.** If you find two independent causes, fix the one that failed the gate; report the second in `open_questions` for its own round/ticket.
- **Flaky ≠ fixed.** A test that passes after your fix but failed for a different reason each of the last 3 runs is still open; say so.
- **Do not touch GWT/schema/tokens to make a failure disappear.** If the oracle itself is wrong, that is a pm/dba/designer decision — stop and return it as an open question.

## Self-check

- [ ] Failure reproduced verbatim before any edit?
- [ ] Every eliminated hypothesis has its probe line?
- [ ] Root cause is a mechanism, one sentence?
- [ ] Fix touched only the surface the mechanism implies?
- [ ] Failed gate re-run with verbatim output + exit code?
- [ ] `root_cause` returned; second issues parked in open_questions?
