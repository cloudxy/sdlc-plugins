---
name: tdd
description: "Use this skill when the spawn packet adds tdd to an implement hat or $tdd. Do NOT use from parent /sdlc or for coverage matrices."
when_to_use: "Spawn packet lists tdd as an implement-hat companion, or $tdd. Do NOT use from parent /sdlc, qa matrices, or GWT edits."
---

# TDD — the GWT is already written; make it run

Companion procedure for **implement hats** (frontend/backend/algo/miner) when the packet adds `tdd`. The spec's GWT rows are the oracle — you never write a new oracle, you execute the existing one. Lane discipline still applies (`impl-evidence` lane_file); this skill says **when** to touch test code relative to product code.

Purpose: a defect caught by a red test inside the implement hat costs one file edit; the same defect caught at verify/review costs a rework round — producer + fresh reviewer + gate re-run.

## The loop (per FR / per ticket slice)

1. **Pick one GWT row** from the ticket's FR (smallest first: happy path, then empty/boundary, then unauthorized/error).
2. **Red.** Write the test for that row against the current code. Run it. Paste the **failing** output + exit code verbatim — this is evidence the test can fail. A test written after the code that has never been red proves nothing.
3. **Green.** Write the minimum product code that makes exactly that row pass. Run the test. Paste passing output.
4. **Refactor** only while green, only within the seam you just touched, re-run after each step.
5. Next GWT row. A row that cannot be tested as written (missing seam, oracle ambiguity) → stop, return it as an open question to pm — do not silently reinterpret the oracle.

## Gotchas

- **Never edit a GWT row to make a test pass.** GWT changes belong to pm; silent oracle drift is a defect the reviewer will catch (dimension 6) — that is a whole rework round wasted.
- **Red must be real.** Red = assertion failure for the right reason, not import error, not fixture crash. Check the failure message names your oracle.
- **No snapshot-approval tests for new behavior.** Approval snapshots freeze whatever the code first did — including the bug.
- **Test the lane's own surface.** frontend tests the component contract, backend the service/API contract; do not reach across lanes to make a test pass (that is a contract question for architect).
- **Evidence = both outputs.** The red run and the green run go into `T-<n>-evidence.md`; a green-only record is incomplete evidence.

## Self-check

- [ ] Every test was red before it was green (both outputs pasted)?
- [ ] No GWT row edited, reinterpreted, or skipped silently?
- [ ] Refactoring only while green, only inside the touched seam?
- [ ] Untestable rows returned as open questions, not improvised?
- [ ] Coverage matrix holes (qa's domain) not pre-empted here — this is per-ticket execution, not the full matrix?
