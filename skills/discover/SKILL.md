---
name: "discover"
description: "Use this skill when the user says /sdlc-discover or /sdlc on a vague L2+ idea with no briefing. Do NOT use for spec.md or code."
when_to_use: "Use when /sdlc-discover, or /sdlc L2+ with no briefing. Do NOT use to write spec.md, schema, or code."
---

# Discover — frame, survey, discuss, falsify, then freeze

**Entry mode:** `full` (default) follows the chain below. `research` follows [references/research-mode.md](references/research-mode.md) and returns after the survey; no HITL, freeze or define. Preserve an explicit command mode.

This window is the **discovery manager**. You keep the user-facing reply (grilling is HITL). Spawn `sdlc-workflow:researcher` / `sdlc-workflow:competitor` for the AFK survey, then `sdlc-workflow:growth` for positioning and highlight hypotheses. Do not handoff. Do not write `spec.md`.

Discovery exists to find **what is worth building and why it would win** — not only to kill bad ideas. Falsify guards against self-deception; the survey and growth tracks supply the insight.

Borrowed: mattpocock **grilling** (design tree, whole frontier per round, recommended answers) and superpowers **brainstorming** (classify, present, **stop until the human confirms** — never spawn pm in the same breath as a summary).

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/productivity/grilling 与 obra/superpowers skills/brainstorming；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745、obra/superpowers@b36e0829c6d0。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

**Order (locked):** Frame → Market ∥ Compete → Growth → Discuss-P → Discuss-S → Falsify → freeze briefing. Do not discuss solutions before the survey. Do not write FR/GWT here.

| Task | Approach |
|---|---|
| **Vague idea / new product change** | Full chain below |
| **Survey only** | Execute `research` mode via its reference |
| **Briefing exists, user says continue** | Stop. Tell them `/sdlc` / resume — define is pm, not you |
| **Kill verdict** | `discovery.status: killed`. Do not spawn pm |

## Gotchas

- **No frame → shopping list.** "See what everyone is doing" without who/space copies competitor features. Frame is ≤5 sentences, no buttons, no FR.
- **Operator ≠ market.** The person in chat decides; real users get an interview script; absent stakeholders get a questionnaire. Do not treat chat consensus as E3.
- **E3 needs a counted snapshot.** Number + source + window (e.g. "12 tenants exported in 30d from warehouse.exports"). Operator chat / one ticket is ≤E1. Do not upgrade.
- **Briefing compresses.** Market/Compete in `briefing.md` are ≤5 lines + links to `00-discover/*.md`. Pasting the survey files is a defect.
- **"Competitor has it" is E0.** Survey compete; then ask whether *our* users have the problem.
- **Present then stop.** Summarising understanding and spawning pm in one message skips the gate (superpowers hard-gate).
- **Status quo is a competitor.** Excel / manual / "don't use us" always sits in the compete set. Empty set without 现状 is a defect.
- **Unquantified Reach is legal; unquantified cannot pass.** Write 未量化. Verdict is kill | narrow | bet | pass — **pass only if every load-bearing row is ≥E2.**
- **Search before 未量化.** Survey hats have WebSearch/WebFetch: public data, reviews, pricing pages and community threads come before "no data". A 未量化 row must say what was searched.
- **A 0→1 bet is a legitimate outcome.** New products rarely reach E2 before building; write the bet with its metric and cheapest validation instead of stalling discovery.
- **Growth reads compete first.** Positioning is derived from the alternatives users actually use — spawn growth only after `compete.md` exists.

## Steps

### 1. Frame (HITL, one round)

Say the classification out loud: spike / bounded-L1 (skip this skill; L0/L1 do not discover) / **product-change** (default).

Ask only what you need for a frame: who we serve, ToB/ToC/both, problem *type* (not the button). Write `00-discover/briefing.md` with Claim stub. `discovery.status: pending`, `phase: Discovering`.

### 2. Survey (AFK, parallel)

Spawn **once each** (native `sdlc-workflow:<role>`, packet v2 with `product_context` = product `strategy.md` + `feature-map.md`, no SKILL.md paste):

- `hat: researcher`, `stage: market`, `task: survey`, `primary_skill: sdlc-workflow:market` → `00-discover/market.md`
- `hat: competitor`, `stage: compete`, `task: survey`, `primary_skill: sdlc-workflow:compete` → `00-discover/compete.md`

If host unknown type: one `general-purpose` fallback that Reads `PLUGIN_ROOT/agents/<role>.md` + the skill. Record `host_spawn`. Then `check-sdlc.sh --require --hat market` / `--hat compete`.

Skip a hat only with `roles_skipped` + why (pure internal tool still writes 现状 in compete).

Load `sdlc-workflow:market` / `compete` only inside those hats, not here.

### 2b. Growth (AFK, after survey)

Spawn **once**: `hat: growth`, `stage: growth`, `task: positioning`, `primary_skill: sdlc-workflow:growth`, inputs `00-discover/compete.md` + `00-discover/market.md` + the frame → `00-discover/growth.md` (≥2 positioning options, ≤3 highlight hypotheses as moments, behaviour-defined segments). Then `check-sdlc.sh --require --hat growth`. Skip only with `roles_skipped: [growth]` + why (internal tool, pure refactor).

### 3. Discuss (HITL)

Load nothing else yet. Work a **design tree**. Each round: every question whose prerequisites are settled; number them; give a recommended answer; **wait**.

- **Discuss-P:** three-question probe (how do they do it today / where it breaks / what they do next). Four role surfaces (buyer / user / tenant admin / platform admin). Conflicts as their own heading. No solution pick.
- **Discuss-S:** only after survey and growth files exist. A/B/C, appetite, ToB/ToC probe card ([product-surfaces.md](references/product-surfaces.md)). Each option states which highlight hypothesis it makes true. Do not adopt a competitor feature as the chosen solution.

Facts (repo, docs, survey files) are your job — spawn no extra hats for grep. Decisions are the user's.

Interview script / questionnaire: [discuss-protocol.md](references/discuss-protocol.md). External answers stay E1 until they come back.

### 4. Falsify (HITL)

Invoke `sdlc-workflow:falsify`. Problem-layer uses survey evidence (triage tree). Solution-layer uses Discuss-S. Verdict: kill | narrow | bet | pass. Bet requires a named metric that later becomes the spec north-star or driver.

Optional: packet `companion_skills: [prototype]` and spawn a writer (designer / general-purpose) for LOGIC/UI/FAKE. Prototype code is not implement evidence.

### 5. Freeze

Complete [templates/briefing.md](templates/briefing.md). Five track headings present (Discuss, Compete, Market, Growth, Falsify). `discovery.status: done` (or `killed`). Open questions as `{id, status, owner, recommended}`.

Ask: "Briefing frozen at `00-discover/briefing.md`. Continue to define (`/sdlc`) or stop here?" **Wait.** Do not spawn pm.

## Self-check

- [ ] Frame written before survey spawns?
- [ ] market.md and compete.md on disk (or skipped with why)? Compete has 现状?
- [ ] growth.md on disk after compete (or growth skipped with why)? Briefing `## Growth` compressed to ≤5 lines + link?
- [ ] Discuss-P before Discuss-S? No FR/GWT in briefing?
- [ ] Falsify has kill criteria and a verdict? Unquantified market did not "pass"?
- [ ] Human confirmed before any define spawn?
- [ ] Briefing Market/Compete are summaries + links, not a paste? No E3 without a counted snapshot?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [discuss-protocol.md](references/discuss-protocol.md) | Grilling rounds, Mom Test script, questionnaire |
| [product-surfaces.md](references/product-surfaces.md) | ToB/ToC probe card in Discuss-S |
| [templates/briefing.md](templates/briefing.md) | Writing the freeze artifact |
