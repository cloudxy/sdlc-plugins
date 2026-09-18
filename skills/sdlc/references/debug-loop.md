# Debug loop — rework respawns with method (6A / 7A)

Read this when the manager is about to respawn a producer hat for the **second or later** rework round (`rework_rounds >= 2` on that hat — G-fresh fails and acceptance `不通过` both count). First-round rework may fix directly. This file is the **manager-side contract** (when to attach, bookkeeping); the producer's procedure is the skill `sdlc-workflow:debug` — the packet's `debug_protocol` field tells the hat to load it. This Reference is never invoked standalone.

Why: a repeated G-fresh fail on the same hat is a hypothesis problem, not an effort problem. Re-running the same producer with the same inputs and hoping is a bare retry.

## The loop (producer runs it, in order)

1. **Reproduce.** One command + exit code that shows the failure verbatim (the failed gate, the failing test, the rejected artifact diff). No reproduction → no fix attempt; return "cannot reproduce" + what you tried.
2. **Isolate.** Bisect the surface until the failure has one smallest trigger. List the hypotheses you eliminated and how (one line each: hypothesis → probe → result).
3. **Root cause, one line.** A sentence that names the mechanism ("router imports ORM, transaction boundary lost", "GWT oracle contradicts FR-3"), not the symptom ("test fails").
4. **Minimal fix.** Touch the smallest surface the mechanism implies. No drive-by refactors in a rework round.
5. **Re-run the failed gate.** Same command as step 1. Paste verbatim output + exit code into `T-<n>-evidence.md` under a `## Debug record` heading: reproduce command, eliminated hypotheses, root cause line, fix summary, re-run output.
6. **Return** `root_cause: <the one line>` to the manager — it goes into the gate record in `state.yaml`.

## Manager rules

- Round 2+ rework packet must set `debug_protocol: <PLUGIN_ROOT>/skills/sdlc/references/debug-loop.md` and require the `root_cause` line in the return.
- A respawn whose gate record lacks `root_cause` (round 2+) is an unfilled packet — do not spawn.
- `rework_rounds >= 3` on the same hat: stop, report systemic (orchestrator-gates §3). Debug-loop does not override the stop rule.

## What this is not

- Not a new hat: the producer hat itself runs the loop.
- Not a SKILL.md: it stays out of the skill-metadata budget.
- Not a substitute for G-fresh: the fix is still judged by a fresh reviewer on the new files.
