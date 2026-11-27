# Technical diagnosis & debug review criteria

Single source of procedure: [debug](../SKILL.md). Apply during standalone `implement/diagnose`, `collect/diagnose`, and rework rounds carrying `debug_protocol`. Diagnosis proves **mechanism from first-hand evidence** before any minimal repair; an inconclusive report with bounded probes and honest limits beats a fabricated root cause every time.

## Expert Bar vs Mediocre Order-Taker

| Dimension | Expert Diagnostician Bar | Mediocre Order-Taker Anti-Pattern |
|---|---|---|
| **Reproduction Fidelity** | Reproduces the exact symptom verbatim before editing; exercises real `click -> observe` event sequences for UI equivalence/interaction claims; labels diagnostic exit `0` as `reproduction confirmed`, never `bug fixed` | Bare-retrying flaky gates hoping for green; comparing static SVGs/CSS classes instead of clicking UI controls; claiming a fix without prior reproduction |
| **First-Hand Evidence vs Guesswork** | Reads the actual DB/Redis/queue/DOM state directly; uses conservation probes (`Σ parts == total`) and failure-set stability (varying = race/state; stable = semantics/schema) to bisect fast | Stacking speculative patches on top of unremoved failed guesses; trusting prior commit messages ("Fixed X") or pagination-truncated UI views |
| **Mechanism Depth** | Names the exact structural/temporal mechanism (e.g. `Router` ORM leak, multi-worker local `dict` divergence, `In-Doubt` timeout treated as `Fail`, `focusout` hiding menu before `click`); separates confirmed, suspected, and ruled-out causes | Reporting symptoms as causes ("test timed out", "API returned 500"); inventing certainty when logs/access are missing |
| **Repair Discipline & Boundaries** | Zero production edits during standalone `diagnose` (`04-verify/diagnosis-<role>.md`); in repair rounds, touches only the mechanism's minimal seam, preserves GWT/schema/tokens, and parks secondary bugs in `open_questions` | Editing GWT rows, coverage matrices, or design tokens to silence a red gate; sneaking drive-by refactors into a rework round |

## Mode-Specific Review Gates

- **Standalone `diagnose` (`04-verify/diagnosis-<role>.md`)**: Uses [diagnosis.md](../templates/diagnosis.md); production source tree remains untouched; distinguishes confirmed mechanism from bounded unknowns and routes the concrete next action (`implement/fix`, `dba`, or `pm` clarification).
- **Rework / `implement/fix` (`## Debug record`)**: Appends reproduction command, `hypothesis -> probe -> result` elimination log, `root_cause` mechanism, minimal fix diff summary, and verbatim re-run (multi-iteration / barrier-tested when fixing a race/flake).
- **Live Incident Context**: Separates immediate authorized operational mitigation from root-cause proof so service restoration is never delayed by investigation.

## Second-Order Scan (Run Before Sign-Off)

1. **Leftover Speculative Edits**: Were all temporary probes and rejected-hypothesis patches cleanly reverted so only the confirmed minimal fix remains?
2. **Sibling Failure Modes**: Does the confirmed mechanism (e.g. missing `tenant_id` scope, `get(field, [])` collapsing `missing` with `empty`, unguarded `rows == 0`) exist on adjacent endpoints/views within the same slice?
3. **Multi-Worker / Cold-Start Parity**: Would this reproduction or fix behave differently across 2+ worker processes, cold interpreter imports, or slow-3G network timing?
4. **Targeted Verification Efficiency**: Did reproduction and verification use sharp targeted commands rather than wasteful full-suite test runs?

## Immediate Return-for-Rework Triggers

- Modifying production source code during a standalone `implement/diagnose` or `collect/diagnose` assignment.
- Editing GWT expectations, `schema.dbml`, coverage matrices, or design tokens to silence a failing check instead of escalating an oracle defect.
- Claiming a flaky/race defect is fixed based on a single retry pass without deterministic reproduction or multi-run concurrency proof.
- Labeling a diagnostic probe's `exit: 0` as `bug fixed` rather than `reproduction confirmed`.
