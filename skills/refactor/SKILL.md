---
name: refactor
description: "Use this skill when the spawn packet marks the ticket as refactor or $refactor. Do NOT use from parent /sdlc or for new FRs."
when_to_use: "Spawn packet marks the ticket maintenance/refactor, or $refactor. Do NOT use from parent /sdlc, new FRs, or migrations."
---

# Refactor — behavior preserved, structure improved

Procedure for **maintenance tickets** (usually L0/L1 lane, any implement hat). A refactor ticket changes **structure without changing behavior**. A behavior change is a separate change objective: identify its acceptance and owner, then let the manager choose the appropriate bug/feature route without forcing full discovery.

Purpose: untracked structural drift is where the next feature's rework loops are born — this procedure keeps drift small and provably behavior-preserving.

## The loop

1. **Characterization first.** Before touching structure, pin current behavior: run the existing gates/tests and paste output. Missing coverage on the seams you will touch → write characterization tests that assert **what the code does today** (not what it should do); a failure may reveal unstable behavior, an incorrect characterization or a real defect; investigate before deciding which.
2. **One seam per step.** Name the seam (file/function/module boundary) in one line. Move/rename/extract within it. Run gates. Commit-able checkpoint.
3. **Behavior diff = zero.** After each step, observable outputs/contracts and relevant budgets remain equivalent. Test imports, internal seams or fixtures may change; explain each adjustment and ensure no weaker behavioral assertion. A passing unchanged assertion alone does not establish equivalence.
4. **Repeat** until the ticket's named goal is met, then stop. "While I'm here" is scope creep — park it in open_questions as its own ticket.
5. **Evidence**: per step, the gate command + exit code under `## Refactor steps` in the evidence file; final summary = seams touched, characterization count, test adaptations and their behavioral justification.

## Gotchas

- **Observable behavior is the invariant.** Use characterization/differential tests and relevant contract/performance checks; justify test adaptations without loosening the accepted behavior.
- **No public-contract renames inside a refactor ticket.** Renaming an exported API/schema shape breaks callers = behavior change; needs its own define→shape cycle (deprecation wrapper first).
- **Do not mix refactor with bug fix.** A defect found mid-refactor gets its own ticket (and its own debug round if it recurs); fixing it here hides it from coverage.
- **Dead code deletion needs the same discipline.** "Surely unused" is a hypothesis — grep callers, cite the search in evidence, then delete.

## Self-check

- [ ] Characterization set existed (or was written) **before** the first structural edit?
- [ ] Each step named one seam and ran the gates?
- [ ] Test adaptations preserve the observable contract and are justified?
- [ ] No behavior change, public-contract rename, or drive-by fix mixed in?
- [ ] Evidence shows per-step command + exit code and the final zero-diff claim?
