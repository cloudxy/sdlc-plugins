---
name: refactor
description: "Use this skill when the spawn packet marks the ticket as refactor or $refactor. Do NOT load in /sdlc or for new FRs."
when_to_use: "Spawn packet marks the ticket maintenance/refactor, or $refactor. Do NOT use from parent /sdlc, new FRs, or migrations."
---

# Refactor — behavior preserved, module depth improved, connascence reduced

Procedure for **maintenance tickets** (usually L0/L1 lane, any implement hat). A refactor ticket **improves internal structure without changing observable behavior**. A behavior change or bug fix is a separate change objective: identify its acceptance and owner, park it in `open_questions`, and let the manager route it without mixing it into structural edits.

## High-order structural targets (what "better structure" actually means)

Do not split code into tiny shallow files just to lower line counts. Every step must move toward one of these concrete engineering targets:

- **Ousterhout Deep Modules & Deletion Test**: increase `hidden complexity ÷ interface surface`. Collapse shallow pass-through wrappers, middleman managers, and fragmented 1-call helpers that fail the Deletion Test (if deleting the boundary removes cognitive friction without duplicating rules across callers, collapse it).
- **Connascence Reduction**: replace strong/dynamic connascence across seams (**Position** long arg lists, **Meaning** magic values/raw dicts, **Temporal** call-order traps, **Shared Mutable State**) with weak static **Name / Narrow Type** connascence; pull unavoidable strong coupling inside a single deep module.
- **DIE (SSOT) vs AHA**: consolidate duplicated **authoritative** business rules, visibility predicates, limits, or error mappings into one canonical source (**DIE**), while resisting premature DRY helpers parameterized by boolean mode flags (`is_admin`, `for_export`) across diverging business actors (**AHA**).
- **SOLID, LoD & Functional Core**: narrow fat DTOs/Props/Ports to what the consumer actually reads (**ISP**); invert concrete infra dependencies behind narrow ports (**DIP**) while preserving exact behavioral/error/nullability parity across implementations (**LSP**); eliminate `a.b.c.d()` train-wreck navigation (**LoD**); extract pure deterministic domain calculations (**Functional Core**) out of stateful I/O shells (**Imperative Shell**) and eliminate process-global mutable state.

## The loop

1. **Characterization first (targeted only).** Before touching structure, pin current observable behavior on the affected seam: run **targeted** existing gates/tests (full-suite runs are forbidden) and paste output + exit code. Where seam coverage is missing, write characterization tests asserting **what the code does today** (inputs, outputs, side effects, error codes). If characterization reveals a latent bug, **do not fix it here** — pin or scope around it and report the defect in `open_questions` for its own ticket.
2. **One seam per step.** Name the single seam and structural target (e.g. "collapse shallow `OrderValidator` pass-through into `OrderService`", "extract pure `allocate_discount_minor` Functional Core") in one line. Move/rename/inline/extract within that seam, then run the targeted gates for a clean checkpoint.
3. **Behavior diff = zero.** Observable contracts, error codes, side effects, and budgets remain equivalent after every step. Test imports, internal wiring, or mocks may adapt to the new seam — explicitly document each test adaptation and prove assertions were **not** weakened.
4. **Stop at the ticket's goal.** Park adjacent "while I'm here" cleanups in `open_questions`.
5. **Evidence**: record pre-edit characterization + per-step targeted command + `exit: 0` under `## Refactor steps` in `impl-evidence.md`, ending with seams touched, characterization count, justified test adaptations, and the zero-behavior-diff summary.

## Gotchas

- **No public-contract renames inside a refactor ticket.** Renaming exported API fields, CLI flags, events, or DB columns breaks callers = behavior change requiring its own `expand-contract` / `shape` cycle.
- **Never mix a bug fix into a refactor.** Fixing an off-by-one or edge defect mid-refactor hides a behavioral change inside a "no behavior change" commit.
- **Dead-code deletion requires proof.** Grep callers, dynamic dispatches, and config/package references first; cite the exact search command in evidence before deleting.
- **Never replace working concrete code with a 1-implementation interface** unless isolating an external I/O boundary for testing or fulfilling an accepted Next/Later variant (YAGNI).

## Self-check

- [ ] Targeted characterization tests ran (or were written and passed) **before** the first structural edit?
- [ ] Each step named one seam + structural principle (Deep Module / Connascence / DIE-AHA / Functional Core / ISP-LoD) and exited `0`?
- [ ] Test wiring adaptations are documented and preserve full behavioral assertion strength?
- [ ] Zero behavior changes, zero public-contract renames, zero drive-by bug fixes mixed in (discoveries parked in `open_questions`)?
- [ ] Only targeted checks ran (no full-suite waste), with verbatim per-step commands + exit codes recorded?
