---
name: tdd
description: "Use this skill when the spawn packet adds tdd to implementation or $tdd. Do NOT load in /sdlc or for coverage matrices."
when_to_use: "Spawn packet lists tdd as an implement-hat companion, or $tdd. Do NOT use from parent /sdlc, qa matrices, or GWT edits."
---

# TDD — the GWT is already written; prove Red then Green

Companion procedure for **implement hats** (`frontend`, `backend`, `algo`, `miner`) when the packet adds `tdd`. The spec's GWT rows are the business oracle — preserve business meaning strictly while deriving technical invariants, conservation laws, concurrency races, and regression cases from accepted contracts/code without asking `pm` to micro-authorize ordinary test design. Lane discipline (`impl-evidence` `lane_file`) still applies.

Purpose: catching an oracle mismatch or boundary race on a targeted Red → Green cycle costs one local edit; letting it escape to verify/review costs a full rework + fresh-reviewer cycle.

## When it applies

Use Red-Green-Refactor for deterministic/controllable behavior (prefer testing through the contract-named seam and pure **Functional Core** domain functions). Statistical/LLM quality uses versioned `eval-set` benchmarks from the lane (`ai`/`model`); read-only inspection tasks write exact test code and expected Red/Green outcomes **without claiming unexecuted runs**. Developer TDD never replaces independent `qa`.

## The loop (targeted execution only — never run the full test suite)

1. **Pick one GWT row or technical invariant** (order: happy path → empty/boundary/illegal-state parse rejection → unauthorized/cross-tenant → concurrency/idempotency/conservation).
2. **Red.** Write a targeted test through the seam already named in the accepted architecture contract or ticket (ask only when neither names a boundary and multiple incompatible seams exist — never re-confirm an accepted contract seam). Run **only that targeted test file/case**:
   - Verify it fails for the **intended assertion reason** naming the oracle — never an `ImportError`, syntax error, or broken fixture.
   - If existing code already satisfies a characterization row, record that honestly; never sabotage working production code just to manufacture a fake Red run.
3. **Green.** Write the minimum product code (parsing at the boundary, pure Functional Core calculation, thin I/O shell) to pass that row. Re-run the targeted test to `exit: 0`.
4. **Refactor while green.** Collapse shallow duplication or tighten types inside the touched seam only, re-running the targeted test after each edit.
5. **Next row.** Genuine business oracle ambiguity (two plausible `Then` readings) → **stop** and return an `open_question` to `pm`; never pick an oracle silently or edit GWT.

## High-order test laws, evidence formatting & gotchas

- **Independent literal expectations (zero tautological tests).** Never compute `expected` using the product's own formula, constants (`DISCOUNT_RATE`), or private helpers (`_cents`) — a test that mirrors implementation math passes by construction even when the formula is wrong. Take literal expected values directly from GWT rows, worked contract examples, or independent hand calculation, and flag existing tautological tests when encountered.
- **Pair example cases with Conservation & Algebraic Invariants.** Where domain math or concurrency applies, add invariant assertions alongside example literals:
  - **Conservation**: `Σ debits == Σ credits`, `on_hand - reserved == available >= 0`, `sum(allocated_line_cents) == order_total_cents`.
  - **Idempotency & Concurrency**: parallel `gather(f(key), f(key))` produces 1 persisted mutation and identical consumer result.
  - **Round-trip / Parse**: `parse(serialize(valid)) == valid`; illegal state combinations rejected at the boundary.
- **Safe Red → Green formatting (prevent `EVIDMISMATCH` false positives).** Automated evidence checkers verify that authoritative final verification commands exit `0`. Therefore:
  - Record pre-implementation failing runs inside `### TDD Red -> Green` in `impl-evidence.md`, explicitly labeled **`Red (expected pre-impl failure, red_exit: 1)`** with the assertion failure excerpt, immediately followed by **`Green (post-impl pass, exit: 0)`**.
  - Keep the final `## 4. 定向自测证据` command block strictly for post-implementation verification commands where every command exits `0`.
- **No snapshot-approval tests for new behavior**, and **never reach across lanes** (e.g. `frontend` mocking `backend` DB internals).

## Self-check

- [ ] Every new behavior/regression test showed a real assertion-level Red before Green (or explicitly recorded read-only / characterization limits without faking runs)?
- [ ] Red output is isolated under `### TDD Red -> Green` as expected pre-impl failure while final verification commands exit `0`?
- [ ] Expected values are independent literals from GWT/worked examples (zero recomputed formulas) + applicable conservation/idempotency invariants?
- [ ] Zero GWT rows edited, reinterpreted, or silently skipped (ambiguities returned to `pm` as `open_questions`)?
- [ ] Only targeted test files/cases executed per cycle (no full-suite runs)?
