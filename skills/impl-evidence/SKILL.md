---
name: impl-evidence
description: "Use this skill when the spawn packet sets lane_file=ui|api|ai|model. Do NOT use from parent /sdlc or to design schema."
when_to_use: "Use this skill when the spawn packet sets lane_file=ui|api|ai|model. Load inside sdlc-workflow:frontend / backend / algo / miner. Do NOT use from parent /sdlc. Do NOT use to design schema or GWT."
---

# Implementation evidence — contract in, command+exit out

Shared implementer procedure. Identity stays with `sdlc-workflow:frontend` / `backend` / `algo` / `miner`. The spawn packet's **`lane_file`** field selects your lane.

**Orient rule 1 (before anything else):** read `lane_file` from the spawn packet.

- `lane_file` missing, empty, or not one of `ui|api|ai|model` → **stop**. Do not read any lane file. Return to the orchestrator: "packet has no valid lane_file".
- Otherwise read **only** `references/<lane_file>.md` and `references/<lane_file>/` below. Other lanes are forbidden reads for this hat (frontend: not api/ai/model; backend: not ui/ai/model; algo: not ui/api/model; miner: not ui/api/ai).

Job: **implement a journey slice that works end-to-end for the user, and leave replayable evidence.** Contract in; command + exit code out; for UI slices, screenshots of the running product against the real backend. Do not drift GWT. Do not invent schema or tokens.

**Read the why first:** the ticket's journey J-n, spec §2 (core value, Aha), the picked prototype screenshots and `design-system.md` (UI), `tracking.md` (events). A ticket implemented without them passes its tests and still misses the product.

| Hat | Lane file (packet `lane_file`) |
|---|---|
| frontend | `ui` → [ui.md](references/ui.md) then [ui/](references/ui/) |
| backend | `api` → [api.md](references/api.md) then [api/](references/api/) |
| algo | `ai` → [ai.md](references/ai.md) then [ai/](references/ai/) |
| miner | `model` → [model.md](references/model.md) then [model/](references/model/) |

## Gotchas

- **This file is the shared protocol, not a fourth implementation style.** After Orient, read the lane file for the hat you are.
- **Evidence is command + exit code pasted verbatim.** "It passed" is not evidence. One evidence file per ticket and lane: `03-impl/T-<n>-<role>-evidence.md` (e.g. `T-3-backend-evidence.md`). Another lane's file for the same ticket never counts for yours.
- **Tests green ≠ slice works.** A UI slice is done only after an integration run against the real backend: walk the journey steps, take screenshots (`bash PLUGIN_ROOT/scripts/ui-evidence.sh <url> 03-impl/screens/T-<n> 375,1440`), look at them, compare with the picked prototype, and write `03-impl/T-<n>-integration.md` ([templates/integration.md](templates/integration.md)). v4 gate `INTEGRATION`.
- **Contract examples first.** Backend publishes example responses or a mock for the slice before building internals so frontend works in parallel; both sides then integrate on the real service.
- **Events ship with the feature.** Implement `tracking.md` events in the same slice (server-side for results, client-side for UI behaviour) and check they fire during the integration run.
- **Contracts are input.** Schema → dba. Tokens → designer. GWT changes → pm. Silent drift is a defect.
- **Layering:** backend Router does not import ORM. Run `scripts/check-layering.py` when touching backend layers.
- **Rework respawns (debug_protocol in packet):** append a `## Debug record` to the evidence file — reproduce command, eliminated hypotheses, one-line root cause, minimal fix, re-run output + exit code (procedure: `sdlc-workflow:debug`).
- **Companion procedures:** packet `companion_skills` may add `tdd` (red before green per GWT row; evidence = both outputs) or `refactor` (maintenance tickets; characterization first, zero assertion edits). They do not change lane discipline.

## Shared self-check

- [ ] Packet `lane_file` present and valid (else you should have stopped)?
- [ ] Only your lane file + lane directory read — no other lane opened?
- [ ] Deliverable path exists on disk?
- [ ] UI slice: integration run on the real backend, screenshots looked at and compared with the prototype?
- [ ] Events from `tracking.md` implemented and seen firing?
- [ ] Evidence uses [templates/impl-evidence.md](templates/impl-evidence.md)?
- [ ] Did not change GWT, schema, or design tokens?

## Templates and scripts — when to read them

| File | Use when |
|---|---|
| [templates/impl-evidence.md](templates/impl-evidence.md) | Every implementer ticket |
| [templates/integration.md](templates/integration.md) | Every UI slice (frontend, with backend): integration run on the real backend with screenshots |
| [templates/eval-set.md](templates/eval-set.md) | algo eval set |
| [templates/model-choice.md](templates/model-choice.md) | algo model + fallback chain |
| [templates/task-spec.md](templates/task-spec.md) | algo task definition |
| [templates/feature-dict.md](templates/feature-dict.md) | miner features with as-of |
| [templates/model-card.md](templates/model-card.md) | miner model card |
| [templates/problem-framing.md](templates/problem-framing.md) | miner action-first framing |
| `scripts/check-layering.py` | backend Router/Service/Repository boundary |

> Shared evidence protocol. Lane footguns stay in `references/<lane>/`.

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
