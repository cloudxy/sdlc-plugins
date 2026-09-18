---
name: "prd-gwt"
description: "Use when shaping product value, journeys, PRD/GWT, metrics or PM acceptance. In sdlc-workflow:pm or $prd-gwt. Do NOT use while /sdlc runs or for schema/code."
when_to_use: "Use when shaping core value and journeys, writing or judging a PRD, GWT, RICE, metrics blueprint, or walking PM acceptance on the build. Load inside sdlc-workflow:pm, or $prd-gwt. Do NOT use while /sdlc is running in this window. Do NOT use for architecture, schema, or implementation."
---

# PRD / GWT / metrics — product definition procedure

Procedure for product definition and PM acceptance. The `sdlc-workflow:pm` agent owns identity and refuse list. Solo entry: `$prd-gwt`. Reviewers and qc load it to judge specs.

Job: **decide what is worth building, make its core value unmistakable, and make every requirement testable and measurable.** Two questions gate every requirement — "does it move the core value path?" and "how will we know it worked?" — and one more gates the release: "does the build actually deliver it?"

| Task | Approach |
|---|---|
| **New feature, briefing frozen** | Read the product layer → JTBD + core value path → opportunity → ≥3 solution concepts ([product-shaping.md](references/product-shaping.md)) → journeys J-n → FR/GWT → NFR → metrics + tracking → scope |
| **No briefing on an L2+ change** | Stop: return the three-question probe to discover. Do not invent a full FR table from a quote |
| **Product layer missing or unfilled** | Fill `strategy.md` + `feature-map.md` from evidence first ([templates/product-strategy.md](templates/product-strategy.md), [templates/feature-map.md](templates/feature-map.md)); mark inferences `[推断]` |
| **"What are the core features?"** | Core value path + the removal test + Kano layering in `feature-map.md` ([product-shaping.md](references/product-shaping.md)) |
| **"Is this worth building?" / prioritize** | Triage + value-path contribution + RICE ([requirement-triage.md](references/requirement-triage.md)) |
| **Review a PRD** | Self-check below, every item |
| **Scope too big** | Appetite slicing along the journey: keep the path to Aha, cut around it |
| **Stage `accept`** | Walk J-n on the build ([acceptance-walkthrough.md](references/acceptance-walkthrough.md)) → `04-verify/accept-pm.md` ([templates/accept-pm.md](templates/accept-pm.md)) |
| **Frozen FRs change** | Re-triage + `superseded` annotation (numbering discipline) |

## Gotchas — things that go wrong without being told

- **Users describe solutions, not problems.** "Add an export button" → three-question probe: how do you do it today, where does it break, what do you do next? The real job is often a collaboration loop, not a button.
- **A requirement list is not a product.** Without the core value path, every FR looks equally important and the team polishes the periphery. Rank by contribution to the path; label peripheral work as peripheral.
- **The first idea is rarely the best.** Compare ≥3 concepts — the user's own, a smaller one, a bolder one — before writing FRs.
- **Journeys make value testable.** A spec without walkable journeys J-n leaves qa with unit-level mappings and acceptance with nothing to walk; the build passes tests and is still unusable.
- **"正确的", "合理的", "友好的" are untestable.** qa cannot write a case from "handle errors appropriately". Ask how much, how fast, what exactly.
- **0→1 has no tickets or data.** Do not block on missing E2 evidence and do not fake it: write hypotheses with the cheapest validation and the metric that will settle them.
- **If RICE confidence is 100% everywhere, you are lying to yourself.** Without data it is 50%.
- **Metrics without events are worthless.** Design the events in define (`01-define/tracking.md`, companion `collect`) or the launch can never be evaluated.
- **"The system provides batch export" is system-speak.** Write "the support lead can export all open tickets in one action".
- **Never commit to a delivery date.** Appetite is a budget, not a schedule.
- **Safety, permissions and data consistency are never cut for appetite.**
- **One user action, one Then.** Two FRs about the same screen must not disagree; NFR one-liners must match the permission matrix and metrics blueprint.
- **Strategic questions are the operator's; operational ones are yours.** Who to serve, positioning, core value and Aha, pricing and paywalls, launch timing, the north star and scope cuts → a `Q-*` row with 类别 战略, options, your recommendation, 状态 待确认, and the dependent FRs marked as waiting. Reversible details inside decided strategy → apply your default (状态 默认, with the reason). Silence is not consent: 2026-09-17, five unanswered strategic calls were written in as 「默认已定」 and spread through four product files.

## Key decisions

### Core value path and core features

```
who → trigger → key action(s) → Aha (sees/gets what) → reason to return
```

A feature is **core** if removing it stops users reaching Aha. Everything else is **support** (makes core usable/sellable: accounts, permissions, billing), **growth** (spreads or converts value), or **experience** (reduces friction). Tag Kano type too (must-be / performance / attractive / indifferent). Keep this in `feature-map.md`; the spec says where this feature sits on the path and which of *faster / stronger / more often / more people* it improves.

### Working backwards — the problem in user terms

Four sentences, all required: ① who (specific role) ② current situation + workaround cost ③ desired outcome in the user's words ④ how we'll know (observable change).

### Solution concepts (≥3) and journeys

Compare concepts on: job coverage, contribution to the value path, whether a highlight moment is possible, difference from alternatives, rough cost (ask architect), risk. Pick one and record why the others lost. Then write key journeys J-n as step tables (user action → what they see → FR) with a success standard (steps / seconds to Aha, completion rate). Every FR anchors to a journey step.

### RICE scoring

`RICE = (Reach × Impact × Confidence) / Effort`. Reach from data; Impact 3/2/1/0.5/0.25; Confidence 100% data / 80% evidence / 50% reasoning / 20% guess; Effort from architect. RICE ranks; it does not decide — compliance may be mandatory, value-path work may outrank a higher score.

### NFR checklist

Performance · Capacity · Availability · Security · Permissions · Compliance · Compatibility · Observability · i18n · Maintainability. Each testable, or explicit `N/A` with a reason.

### Metrics blueprint — three layers

North star (one, closest to user value, from `metrics.yaml`) · drivers (2–4, directly moved by this feature) · guardrails (≥2 with red lines). Every metric has formula, source, window and target; every new data need becomes an event in `tracking.md`.

### Scope cutting with appetite

Budget first, scope follows. Cut **around** the path to Aha, not through it: by role → scenario → volume → automation → format. Cut items go to Out of Scope with "next round / won't do". Exceeding appetite by 50% → stop and re-judge.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | `00-discover/briefing.md` (L2+) · product `strategy.md`, `feature-map.md`, `growth.md`, `data/metrics.yaml`, `data/tracking-plan.yaml` · requirement pool from ops · compete / market notes |
| **Output** | `01-define/spec.md` ([templates/spec.md](templates/spec.md); `spec-s.md` for L1/L2-short) · `01-define/tracking.md` when `tracking: yes` · product `strategy.md` / `feature-map.md` updates + delta rows returned to the manager · `04-verify/accept-pm.md` at stage accept |
| **Downstream** | designer (directions, flows) · architect (options, tickets) · qa (GWT → cases, J-n → E2E) · growth (claims) · analyst (metrics) |
| **Refuse** | Technical choices · table schemas · API shapes · test cases · schedule commitments |

## Self-check (before delivery)

**Value & shape:**
- [ ] Core value path written; this feature's position and effect on it stated?
- [ ] ≥3 solution concepts compared; the choice and the losers' reasons recorded?
- [ ] Key journeys J-n are walkable step tables with a success standard; every FR anchors to a step?
- [ ] Growth's highlight hypotheses reflected as moments in a journey (or explicitly rejected)?
- [ ] Hypotheses labelled with validation method and metric (no fake E2+)?

**Specification:**
- [ ] Every FR has ≥3 GWT (happy + empty/boundary + unauthorized); no untestable words?
- [ ] One user action has one Then; NFR/matrix/blueprint agree with FRs?
- [ ] State-dependent FRs list legal and illegal transitions?
- [ ] NFR walked through all 10 categories?
- [ ] No technical decisions made for downstream?

**Metrics & scope:**
- [ ] North star / drivers / guardrails with ids, baselines, targets?
- [ ] `tracking.md` written (tracking: yes) or `埋点：N/A（理由）`?
- [ ] Appetite declared; out-of-scope listed; security/permissions/consistency not cut?
- [ ] Open questions carry a recommended default?
- [ ] Product layer updated (`strategy.md` / `feature-map.md`) and the delta row returned (the manager records it)?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [product-shaping.md](references/product-shaping.md) | Before any FR: JTBD, core value path and Aha, removal test + Kano, opportunity–solution tree, MVP skeleton, 0→1 hypothesis mode |
| [requirement-triage.md](references/requirement-triage.md) | Triaging requirements, digging for the real problem behind solution-speak, RICE |
| [gwt-authoring.md](references/gwt-authoring.md) | Writing GWT, fixing untestable words, enumerating edge cases, one-oracle rule |
| [metrics-blueprint.md](references/metrics-blueprint.md) | Designing metrics and instrumentation gaps |
| [acceptance-walkthrough.md](references/acceptance-walkthrough.md) | Stage accept: walking journeys on the build, severity, verdict |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified auto_agents product-contract traps (xlsx vs Excel, dual public gates) |
| [templates/spec.md](templates/spec.md) · [templates/user-story.md](templates/user-story.md) | Writing the spec / lightweight stories |
| [templates/product-strategy.md](templates/product-strategy.md) · [templates/feature-map.md](templates/feature-map.md) | Bootstrapping or updating the product layer |
| [templates/accept-pm.md](templates/accept-pm.md) | Writing `04-verify/accept-pm.md` |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
