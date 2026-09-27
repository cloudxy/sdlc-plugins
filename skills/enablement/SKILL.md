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
| **Adoption/support change at any lane** | Fill [templates/enablement.md](templates/enablement.md): first-success guide, support handoff and announcement draft, scoped to the audience and the actual surface (UI, CLI or API) — not a fixed number of personas or FAQs |
| **Users don't know it shipped** | Section 5 (user-facing notes). Do not open a new FR |
| **Long release notes** | [templates/release-notes.md](templates/release-notes.md) is the long form of section 5; link it from there instead of keeping two versions |
| **Support cannot answer** | Section 4 (relevant Q&A + escalation). Do not write runbooks |
| **Triage: product already can, user doesn't know** | This file **is** the deliverable. Do not invent FRs |

## Gotchas

- **People, not machines.** No kubectl, rollback, alert routing, secrets, or CI. That is sre.
- **Use verified product facts.** Reference applicable acceptance/build evidence and the accepted flow; changed promotional claims require growth verification (`04-verify/accept-growth.md` wins a conflict), but an unchanged internal support procedure need not create a marketing task. Positioning and campaigns belong to growth.
- **"Available now" needs deployment evidence.** Before saying it, reference SRE's executed checklist (deployment, version, environment and rollout audience) or the distribution record of a desktop/library release. A QC pass alone does not establish availability. Drafts written earlier label availability as future.
- **Writing is not publishing.** Sending or publishing needs existing explicit authorization and is recorded separately from finishing the document.
- **Do not redraw IA.** Cite designer flow / edge-states for the entry. If the entry is missing, return an open question to designer — do not sketch.
- **Do not write GWT.** First-success steps here are for humans; Given/When/Then stays in spec.
- **ToB ≠ ToC copy.** Tenant-admin menu path vs logged-out activation. Name the surface.
- **「运营环境」is forbidden.** Say 预发 / 生产.
- **sre's checklist missing is not your failure.** `--hat deliver` does not require this file; `--hat enablement` does not require checklist.md.

## Self-check

- [ ] Affected user/admin/support surfaces identified or N/A with reason?
- [ ] Entry cites designer (or open question), not a new wireframe?
- [ ] First-success path for empty tenant or logged-out user (or the CLI/API equivalent)?
- [ ] Support answers cover likely failure/confusion paths and name the escalation owner?
- [ ] User-facing wording, no internal code names; claims match the verified ones?
- [ ] "Available now" backed by a deployment or distribution record, otherwise labelled future?
- [ ] No rollback / kubectl / alert routing, and nothing sent or published without authorization?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [templates/enablement.md](templates/enablement.md) | Writing `06-deliver/enablement.md` |
| [templates/release-notes.md](templates/release-notes.md) | Section 5 needs a full release note |

Apply [references/role-quality.md](references/role-quality.md) for the quality of the first-success path and support handoff.
