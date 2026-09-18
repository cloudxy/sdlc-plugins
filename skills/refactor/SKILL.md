---
name: refactor
description: "Use this skill when the spawn packet marks the ticket as refactor or $refactor. Do NOT use from parent /sdlc or for new FRs."
when_to_use: "Spawn packet marks the ticket maintenance/refactor, or $refactor. Do NOT use from parent /sdlc, new FRs, or migrations."
---

# Refactor — behavior preserved, structure improved

Procedure for **maintenance tickets** (usually L0/L1 lane, any implement hat). A refactor ticket changes **structure without changing behavior**. The moment behavior changes, it is a feature — stop and send it back to define (`/sdlc`, pm hat); do not smuggle an FR through a refactor.

Purpose: untracked structural drift is where the next feature's rework loops are born — this procedure keeps drift small and provably behavior-preserving.

## The loop

1. **Characterization first.** Before touching structure, pin current behavior: run the existing gates/tests and paste output. Missing coverage on the seams you will touch → write characterization tests that assert **what the code does today** (not what it should do); red is a bug in your test, fix the test.
2. **One seam per step.** Name the seam (file/function/module boundary) in one line. Move/rename/extract within it. Run gates. Commit-able checkpoint.
3. **Behavior diff = zero.** After each step, the characterization set passes with no assertion edits. If an assertion needed editing, you changed behavior — revert the step or reclassify the ticket.
4. **Repeat** until the ticket's named goal is met, then stop. "While I'm here" is scope creep — park it in open_questions as its own ticket.
5. **Evidence**: per step, the gate command + exit code under `## Refactor steps` in the evidence file; final summary = seams touched, characterization count, assertion edits (must be 0).

## Gotchas

- **Zero assertion edits is the invariant.** Any edit to a characterization assertion converts this ticket into a behavior change — wrong lane, wrong gate.
- **No public-contract renames inside a refactor ticket.** Renaming an exported API/schema shape breaks callers = behavior change; needs its own define→shape cycle (deprecation wrapper first).
- **Do not mix refactor with bug fix.** A defect found mid-refactor gets its own ticket (and its own debug round if it recurs); fixing it here hides it from coverage.
- **Dead code deletion needs the same discipline.** "Surely unused" is a hypothesis — grep callers, cite the search in evidence, then delete.

## Self-check

- [ ] Characterization set existed (or was written) **before** the first structural edit?
- [ ] Each step named one seam and ran the gates?
- [ ] Zero characterization assertion edits across the whole ticket?
- [ ] No behavior change, public-contract rename, or drive-by fix mixed in?
- [ ] Evidence shows per-step command + exit code and the final zero-diff claim?
