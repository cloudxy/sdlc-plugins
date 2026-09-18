---
name: "signals"
description: "Use this skill when the spawn packet names hat ops or $signals. Do NOT use from parent /sdlc or for RICE ranking."
when_to_use: "Use this skill when the spawn packet names hat ops or the user types $signals / names this hat. Do NOT use from parent /sdlc. Do NOT use for RICE ranking or feature design."
---

# Signals — 产品运营的「听」（不是运维）

This is the **product-operations** listen track on hat `ops`. Deploy, rollback, alerts, and incidents belong to `sre`. Do not write kubectl or runbooks here.

Job: **translate scattered user voices into evidence-backed signals**, and translate launch data into honest assessments.

| Task | Approach |
|---|---|
| **Aggregate user feedback** | Signal extraction: each = source + affected users + frequency + initial recommendation |
| **Competitor analysis** | If this change already has `00-discover/compete.md`, cite it — do not rewrite the snapshot. Long battlecards only for P9 / continuous listen |
| **Growth review** | Compare against original assumptions (predicted vs actual) — not just good news |
| **Release announcement** | User-perspective language, not internal jargon; only claims verified in `04-verify/accept-growth.md` |

## Gotchas

- **"Users all want this" is not a signal.** Ask: which users? How many? Where did they say it? Without source evidence, the signal is an opinion, not data.
- **"Competitor X has this feature" is not analysis.** Three layers: is X a direct competitor? Is the feature core to their value prop or a checkbox? Should we borrow, avoid, or differentiate?
- **P9 review must compare against original assumptions.** If P0 predicted "this will reduce ticket time by 30%" and it reduced by 5%, say so. Only reporting good data is self-deception.
- **Calendar pressure is not a signal.** "CEO wants it Friday" has no source count and is not a RICE input. Write it as a constraint for `pm`. Do not assign P0 or reorder the backlog.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Support tickets / user comments / competitor updates / growth data |
| **Output** | `requirement-pool.md` (signals with evidence) · `feedback-digest.md` (themes + assumption comparison) · `release-notes.md` |
| **Downstream** | `pm` (signals become requirement candidates) · P9 digest feeds back into next P0 |
| **Refuse** | Prioritizing requirements (→ pm's RICE call) · designing features (→ pm) · deploy/rollback/alerts (→ sre / 运维) |

## Self-check

- [ ] Every signal has a source (ticket number / interview / data)?
- [ ] Competitor analysis gives borrow/avoid/differentiate (not just "they have it")?
- [ ] P9 review compares against original P0 assumptions?
- [ ] Growth data has time window and metric definition?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [signal-quality.md](references/signal-quality.md) | Scoring feedback, source evidence, frequency |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified auto_agents traps (code+test / ESC / gate only) |
| [templates/requirement-pool.md](templates/requirement-pool.md) | Signal pool for pm |
| [templates/competitor-analysis.md](templates/competitor-analysis.md) | Borrow / avoid / differentiate |
| [templates/release-notes.md](templates/release-notes.md) | User-facing launch notes |

> Signal discipline from: `anthropics/skills@41bbe19` (internal-comms SKILL.md type-routing pattern, 2026-09-03)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
