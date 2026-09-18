---
name: "enablement"
description: "Use this skill when the spawn packet names ops stage enablement or $enablement. Do NOT use from parent /sdlc or for deploys."
when_to_use: "Packet hat ops + stage enablement, or $enablement. Do NOT use from parent /sdlc or for deliver/rollback."
---

# Enablement — 产品运营的「教 / 开 / 告」（不是运维）

Job: **people can find it, finish first success, and support can answer.** Load inside `sdlc-workflow:ops` when `stage: enablement`. Deploy, rollback, alerts stay on `sre` / `deliver`.

This is the teach track of product operations. The listen track is `signals`. Same hat, different artifact.

| Task | Approach |
|---|---|
| **L3+ after qc** | Fill [templates/enablement.md](templates/enablement.md) |
| **Users don't know it shipped** | Section 5 (user-facing notes). Do not open a new FR |
| **Support cannot answer** | Section 4 (three Q&A + escalate). Do not write runbooks |
| **Triage: product already can, user doesn't know** | This file **is** the deliverable. Do not invent FRs |

## Gotchas

- **People, not machines.** No kubectl, rollback, alert routing, secrets, or CI. That is sre.
- **Say only what growth verified.** User-facing notes and support answers use the claims marked verified or rewritten in `04-verify/accept-growth.md`; positioning and campaigns belong to growth.
- **Do not redraw IA.** Cite designer flow / edge-states for the entry. If the entry is missing, return an open question to designer — do not sketch.
- **Do not write GWT.** First-success steps here are for humans; Given/When/Then stays in spec.
- **ToB ≠ ToC copy.** Tenant-admin menu path vs logged-out activation. Name the surface.
- **「运营环境」is forbidden.** Say 预发 / 生产.
- **sre's checklist missing is not your failure.** `--hat deliver` does not require this file; `--hat enablement` does not require checklist.md.

## Self-check

- [ ] Four-role surfaces this round named or N/A?
- [ ] Entry cites designer (or open question), not a new wireframe?
- [ ] First-success path for empty tenant or logged-out user?
- [ ] Three support Q&As + who to escalate?
- [ ] User-facing wording, no internal code names?
- [ ] No rollback / kubectl / alert routing?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [templates/enablement.md](templates/enablement.md) | Writing `06-deliver/enablement.md` |

Apply [references/role-quality.md](references/role-quality.md) for the quality of the first-success path and support handoff.
