---
name: "discover"
description: "Use this skill when the user says /sdlc-discover or /sdlc on a vague L2+ idea with no briefing. Do NOT use for spec.md or code."
when_to_use: "Use when /sdlc-discover, or /sdlc L2+ with no briefing. Do NOT use to write spec.md, schema, or code."
---

# Discover — frame, survey, discuss, falsify, then freeze

**Entry mode:** `full` (default) follows the chain below. `research` follows [references/research-mode.md](references/research-mode.md) and returns after the survey; no HITL, freeze or define. Preserve an explicit command mode.

This window is the **discovery manager**. You keep the user-facing reply (grilling is HITL). Spawn `sdlc-workflow:researcher` / `sdlc-workflow:competitor` for the AFK survey, then `sdlc-workflow:growth` for positioning and highlight hypotheses. Do not handoff. Do not write `spec.md`.

Discovery exists to find **what is worth building and why it would win** — not only to kill bad ideas. Falsify guards against self-deception; the survey and growth tracks supply the insight.

Borrowed: mattpocock **grilling** (design tree, whole frontier per round, recommended answers) and superpowers **brainstorming** (classify, present, resolve consequential choices with the human when existing authority does not already settle them).

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/productivity/grilling 与 obra/superpowers skills/brainstorming；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745、obra/superpowers@b36e0829c6d0。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

**Default order for a new uncertain product direction:** Frame → relevant research → decision discussion → assumption checks → freeze. Select research by unresolved questions; reuse accepted evidence and authorized decisions. Market/compete/growth are conditional tasks, not mandatory ceremony. Do not write FR/GWT here.

| Task | Approach |
|---|---|
| **Vague idea / new product change** | Full chain below |
| **Survey only** | Execute `research` mode via its reference |
| **Briefing exists, user says continue** | Return to the sdlc manager with the accepted briefing; do not redo discovery or request the same authorization |
| **Kill verdict** | `discovery.status: killed`. Do not spawn pm |

## Gotchas

- **No frame → shopping list.** "See what everyone is doing" without who/space copies competitor features. Frame is ≤5 sentences, no buttons, no FR.
- **Operator ≠ market.** The person in chat decides; real users get an interview script; absent stakeholders get a questionnaire. Do not treat chat consensus as E3.
- **E3 needs a counted snapshot with relevant scope.** Number + source + window (e.g. "12 tenants exported in 30d from warehouse.exports"). Operator chat / one ticket is ≤E1. Do not upgrade.
- **Briefing compresses.** Market/Compete in `briefing.md` are ≤5 lines + links to `00-discover/*.md`. Pasting the survey files is a defect.
- **"Competitor has it" is E0.** Survey compete; then ask whether *our* users have the problem.
- **Honor existing authority.** Present unresolved decisions for confirmation; an accepted briefing and an explicit instruction to continue do not require a second confirmation.
- **Status quo is a competitor.** Excel / manual / "don't use us" always sits in the compete set. Empty set without 现状 is a defect.
- **Unquantified Reach is legal; unquantified cannot pass.** Write 未量化. Verdict is kill | narrow | bet | pass — pass only when the scoped assumptions have sufficiently relevant evidence under the canonical assumption-testing method.
- **Investigate relevant sources before claiming absence.** Use [evidence.md](references/evidence.md); internal operational facts need not be replaced with generic web research. Name unavailable evidence and the consequence for the decision.
- **A 0→1 bet is a legitimate outcome.** New products rarely reach E2 before building; write the bet with its metric and cheapest validation instead of stalling discovery.
- **Growth reads compete first.** Positioning is derived from the alternatives users actually use — spawn growth only after `compete.md` exists.

## Scope selection

Record the unresolved decision, existing evidence/authorization, selected research tasks and why omitted tracks are unnecessary. New audience/business-model uncertainty may require the full chain; a bounded accepted change can proceed using its defect/contract and a focused risk check. Role surfaces and option count follow the actual product. Evidence grades are defined only in [evidence.md](references/evidence.md).

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

Spawn **once**: `hat: growth`, `stage: growth`, `task: positioning`, `primary_skill: sdlc-workflow:growth`, inputs `00-discover/compete.md` + `00-discover/market.md` + the frame → `00-discover/growth.md` (scope and alternatives per growth skill). Then `check-sdlc.sh --require --hat growth`. Skip only with `roles_skipped: [growth]` + why (internal tool, pure refactor).

### 3. Discuss (HITL)

Load nothing else yet. Work a **design tree**. Each round: ask the consequential unresolved questions whose prerequisites are settled; number them, recommend answers, and wait only for decisions not covered by existing authority.

- **Discuss-P:** three-question probe (how do they do it today / where it breaks / what they do next). Applicable role surfaces (for example buyer / user / tenant admin / platform admin). Conflicts as their own heading. No solution pick.
- **Discuss-S:** after evidence relevant to the decision is available or its absence is explicit. Credible alternatives when unresolved, appetite, ToB/ToC probe card ([product-surfaces.md](references/product-surfaces.md)). Each option states which highlight hypothesis it makes true. Do not adopt a competitor feature as the chosen solution.

Facts (repo, docs, survey files) are your job — spawn no extra hats for grep. Decisions are the user's.

Interview script / questionnaire: [discuss-protocol.md](references/discuss-protocol.md). External answers stay E1 until they come back.

### 4. Falsify (HITL)

Apply [assumption-testing.md](references/assumption-testing.md); `falsify` remains a compatibility entry to that same method. Problem-layer uses survey evidence (triage tree). Solution-layer uses Discuss-S. Verdict: kill | narrow | bet | pass. Bet requires a named metric that later becomes the spec north-star or driver.

Optional: use registered `designer/market/prototype` task for a scoped experiment. Prototype code is not implement evidence.

### 5. Freeze

Complete [templates/briefing.md](templates/briefing.md). Five track headings present (Discuss, Compete, Market, Growth, Falsify). `discovery.status: done` (or `killed`). Open questions as `{id, status, owner, recommended}`.

If continuation is already authorized, return the frozen briefing to the sdlc manager for define. Otherwise present the concrete decision and await only the missing authorization. A survey-only request ends here.

## Self-check

- [ ] Frame written before survey spawns?
- [ ] market.md and compete.md on disk (or skipped with why)? Compete has 现状?
- [ ] growth.md on disk after compete (or growth skipped with why)? Briefing `## Growth` compressed to ≤5 lines + link?
- [ ] Discuss-P before Discuss-S? No FR/GWT in briefing?
- [ ] Falsify has kill criteria and a verdict? Unquantified market did not "pass"?
- [ ] Consequential decisions have an explicit current or prior authority reference?
- [ ] Briefing Market/Compete are summaries + links, not a paste? No E3 without a counted snapshot?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [discuss-protocol.md](references/discuss-protocol.md) | Grilling rounds, Mom Test script, questionnaire |
| [product-surfaces.md](references/product-surfaces.md) | ToB/ToC probe card in Discuss-S |
| [templates/briefing.md](templates/briefing.md) | Writing the freeze artifact |
