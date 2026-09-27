---
name: "signals"
description: "Use this skill when the spawn packet names hat ops for signals (listen), or $signals. Do NOT use from parent /sdlc or for release notes."
when_to_use: "Spawn packet hat ops with stage signals (task listen), or $signals. Do NOT use from parent /sdlc. Do NOT use for enablement or release notes (ops stage enablement), RICE ranking or feature design."
---

# Signals — 产品运营的「听」（不是运维）

This is the **product-operations** listen track on hat `ops`. Deploy, rollback, alerts, and incidents belong to `sre`. Do not write kubectl or runbooks here. The teach track (first-success guide, support handoff, release notes) is `enablement` — same hat, different task.

Job: **translate scattered user voices into evidence-backed signals**, while preserving source scope and uncertainty.

| Task | Approach |
|---|---|
| **Aggregate user feedback** | Signal extraction: each = source + affected users + frequency + initial recommendation |
| **Competitor signal** | Capture the dated observation; hand the analysis to compete and reference its canonical result |
| **Growth feedback** | Reference the analyst readout for effects; collect qualitative feedback without a second statistical readout |
| **Incident postmortem as input** | Cite the postmortem (project `.sdlc/_lessons.md` or the incident report) as a source; do not redo the diagnosis |
| **Release announcement request** | Route to enablement; signals does not own release copy |
| **Product cycle digest** (`cycle/signals-digest`) | For the cycle's window: dedupe new voices into the product-level signal store ([templates/signal-store.md](templates/signal-store.md), location `signals_path`) — you are its only writer; take the next free `SIG-<yyyymm>-<n>`, never reuse an ID — then write `outputs/signals-digest.md` in the cycle directory: new and repeated signals, themes, and candidate requirements as proposals for pm |

## Gotchas

- **"Users all want this" is not a signal.** Ask: which users? How many? Where did they say it? Without source evidence, the signal is an opinion, not data.
- **"Competitor X has this feature" is not analysis.** Triage with three questions — is X a direct competitor? Is the feature core to their value prop or a checkbox? Would we borrow, avoid, or differentiate? — mark any lean as preliminary and send the analysis to compete.
- **A feedback digest compares against the original assumptions.** If the briefing or spec predicted "this will reduce ticket time by 30%" and it reduced by 5%, say so. Only reporting good data is self-deception.
- **Calendar pressure is not a signal.** "CEO wants it Friday" has no source count and is not a RICE input. Write it as a constraint for `pm`. Do not assign P0 or reorder the backlog.
- **One loud customer is one customer.** Ten tickets from one customer are one affected customer and ten contacts; report both, not ten users. A quoted request is evidence of that person's request, not proof of market demand.

## Evidence unit

Record per signal: signal ID, original source and date, observation window, affected surface/version, distinct users/accounts, repeated contact count and collection bias. Separate raw observation, interpretation, proposed action and urgency constraint. Keep raw sensitive data in its authorized source; summaries reference it.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Support tickets / user comments / competitor updates / growth data / postmortems |
| **Output** | `01-define/requirement-pool.md` (registry gate path: this feature's digest of signals with evidence, [templates/requirement-pool.md](templates/requirement-pool.md)) · a feedback digest (themes + assumption comparison) when the task asks for one |
| **Downstream** | `pm` (signals become requirement candidates) · the feedback digest feeds the next discovery/define round |
| **Refuse** | Prioritizing requirements (→ pm's RICE call) · designing features (→ pm) · comparative analysis (→ compete) · release copy (→ enablement) · deploy/rollback/alerts (→ sre / 运维) |

When the project keeps a canonical backlog of raw signals, it is the source; the feature digest references its stable IDs instead of making parallel copies. PM decides prioritization; compete owns comparative analysis; retro owns outcome interpretation; enablement owns support and release copy.

## Self-check

- [ ] Every signal has a source (ticket number / interview / data) and a date?
- [ ] Distinct users/accounts separated from repeated contacts?
- [ ] Competitor observations reference compete analysis rather than duplicating it?
- [ ] The digest compares against the original assumptions (briefing/spec predictions)?
- [ ] Growth data has time window and metric definition?
- [ ] No priority assigned, no release copy written?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [signal-quality.md](references/signal-quality.md) | Scoring feedback, source evidence, frequency |
| [templates/requirement-pool.md](templates/requirement-pool.md) | Signal pool for pm |

> Signal discipline from: `anthropics/skills@41bbe19` (internal-comms SKILL.md type-routing pattern, 2026-09-03)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
