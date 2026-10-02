---
name: "discover"
description: "Use this skill when the user says /sdlc-discover or needs help shaping unclear needs. Do NOT use for spec.md or production code."
when_to_use: "Use for unclear needs or unresolved product choices at any delivery size. Reuse accepted decisions. Do NOT write spec.md or production code."
---

# Discover — co-create needs and prepare the next decision

**Entry mode:** `full` (default) selects relevant steps below. `research` follows [references/research-mode.md](references/research-mode.md) and returns after the survey; no HITL, freeze or define. Preserve an explicit command mode; without commands (Codex), an explicit `mode:` or the command name in the request counts as the command.

This window is the **discovery manager**. Keep the user-facing conversation. When research is needed, select `sdlc-workflow:researcher` / `sdlc-workflow:competitor`, then growth if positioning is unresolved. Do not handoff the conversation or write `spec.md`.

Discovery exists to find **what is worth building and why it would win** — not only to kill bad ideas. Falsify guards against self-deception; the survey and growth tracks supply the insight.

Borrowed: mattpocock **grilling** (decision dependencies) and superpowers **brainstorming** (resolve consequential choices not already settled by authority). The shared [discussion method](references/discuss-protocol.md) adds progressive elicitation, examples and revisable understanding.

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/productivity/grilling 与 obra/superpowers skills/brainstorming；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745、obra/superpowers@b36e0829c6d0。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

**For a new uncertain direction:** form a provisional frame, discuss and research what is unclear, check load-bearing assumptions, then accept the current slice. Move back when new information changes the problem or solution. Select research by unresolved questions; reuse accepted evidence and authorized decisions. Market/compete/growth are conditional tasks. Do not write FR/GWT here.

| Task | Approach |
|---|---|
| **Vague idea / new product change** | Use the discussion method and select relevant steps below |
| **Bounded ambiguity / later refinement** | Clarify the consequential gap in the existing work brief; no full survey or new state just for a short exchange |
| **Survey only** | Execute `research` mode via its reference |
| **Briefing exists, user says continue** | Resume its decisions, hypotheses and open questions; return the accepted scope to the manager without repeating settled questions |
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

### 1. Frame progressively (HITL)

Read [discuss-protocol.md](references/discuss-protocol.md) when needs or choices are unclear. Identify the uncertainty before assigning a delivery lane. A small change may need clarification; a large accepted change may not need rediscovery.

Build a provisional understanding of who/context/outcome. If the user cannot answer, offer tentative scenarios or examples to react to. Do not assume a hidden complete brief or force a choice. With an established feature workspace, keep Claim and unknowns in `00-discover/briefing.md`; full discovery uses `discovery.status: pending`, `phase: Discovering`. A bounded exchange uses its existing work brief; conversation-only exploration can retain a compact summary until an artifact location is established.

### 2. Survey (AFK, parallel)

For each selected track, spawn **once** (native `sdlc-workflow:<role>`, packet v2 with `product_context` = product `strategy.md` + `feature-map.md`, no SKILL.md paste):

- `hat: researcher`, `stage: market`, `task: survey`, `primary_skill: sdlc-workflow:market` → `00-discover/market.md`
- `hat: competitor`, `stage: compete`, `task: survey`, `primary_skill: sdlc-workflow:compete` → `00-discover/compete.md`

If host unknown type: one fallback with the host's generic type (`general-purpose`; Codex `default`; Kimi `coder`; [hosts.md](../sdlc/references/hosts.md)) that Reads `PLUGIN_ROOT/agents/<role>.md` + the skill. Record `host_spawn`. Then `check-sdlc.sh --require --hat market` / `--hat compete`.

For a full discovery record, document omitted tracks with `roles_skipped` + why. A bounded exchange need not manufacture survey files; if compete is selected, include 现状 even for an internal tool.

Load `sdlc-workflow:market` / `compete` only inside those hats, not here.

### 2b. Growth (AFK, after survey)

Spawn **once**: `hat: growth`, `stage: growth`, `task: positioning`, `primary_skill: sdlc-workflow:growth`, inputs `00-discover/compete.md` + `00-discover/market.md` + the frame → `00-discover/growth.md` (scope and alternatives per growth skill). Then `check-sdlc.sh --require --hat growth`. Skip only with `roles_skipped: [growth]` + why (internal tool, pure refactor).

### 3. Discuss (HITL)

Follow [discuss-protocol.md](references/discuss-protocol.md). Choose the next helpful move from the current uncertainty. Separate eliciting needs from recommending a decision. Preserve facts, hypotheses, decisions and corrections in the current brief; revisit only the affected scope when understanding changes.

- **Discuss-P:** use relevant parts of the three-question probe or scaffolding to understand context, difficulties and intended progress. Consider applicable roles and conflicts; reuse known answers. Do not prematurely choose a solution.
- **Discuss-S:** after relevant evidence is available or its absence explicit. Compare credible alternatives for unresolved choices, appetite and relevant [product surfaces](references/product-surfaces.md). If growth hypotheses exist, explain their relation to each option. A competitor feature alone does not decide the solution.

Facts (repo, docs, survey files) are your job — spawn no extra hats for grep. Decisions are the user's.

Interview scripts and questionnaires use the same reference. Proposed interviews are not observations; grade actual returns using evidence.md.

### 4. Falsify (HITL)

Apply [assumption-testing.md](references/assumption-testing.md); `$falsify` is only a deprecated compatibility entry to that same method (sunset 2026-12-31). Problem-layer uses survey evidence (triage tree). Solution-layer uses Discuss-S. Verdict: kill | narrow | bet | pass. Bet requires a named metric that later becomes the spec north-star or driver.

Optional: use registered `designer/market/prototype` for a scoped learning material or experiment. An inline sketch can clarify a question without delegation; neither sketches nor prototype code establish implementation or market success.

### 5. Freeze

Apply the discussion method's readiness criteria to the current slice. Complete [templates/briefing.md](templates/briefing.md) for full discovery; preserve its five track headings and explain skipped research. Mark `discovery.status: done` only for the accepted slice (or `killed`). Open questions include owner, recommendation, decision source/status and blocked scope; future questions do not require all-unknowns closure. Partial readiness stays explicit and uses scoped-work routing, not a false full-completion claim.

Freeze means the scope is ready for its next action, not that the hypothesis verdict is `pass`: an authorized bounded `bet` or accepted `narrow` can proceed. Missing evidence alone does not block authorized exploration or select a bet verdict. If scenario, investment boundary or metric is unknown, keep the verdict pending; obtain the missing context before prescribing test counts/thresholds. Do not re-ask approval of the same direction.

Return the accepted briefing to the sdlc manager for define when continuation is authorized. `define` is a stage, not a `/sdlc-define` command; use registered routing, and never claim a handoff ran if tools were unavailable. Otherwise present the concrete decision and await only missing authority. Survey-only stops after its result.

## Self-check

- [ ] Frame written before survey spawns?
- [ ] market.md and compete.md on disk (or skipped with why)? Compete has 现状?
- [ ] growth.md on disk after compete (or growth skipped with why)? Briefing `## Growth` compressed to ≤5 lines + link?
- [ ] Discuss-P before Discuss-S? No FR/GWT in briefing?
- [ ] Falsify has kill criteria and a verdict? Unquantified market did not "pass"?
- [ ] Consequential decisions have an explicit current or prior authority reference?
- [ ] Uncertainty selected the dialogue depth; an unanswered prompt got helpful scaffolding; rejected options and corrected goals were respected?
- [ ] Current-slice readiness, residual hypotheses and blocked consumers recorded without re-asking settled decisions?
- [ ] Briefing Market/Compete are summaries + links, not a paste? No E3 without a counted snapshot?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [discuss-protocol.md](references/discuss-protocol.md) | Unclear needs, conversation starters, corrections, readiness, interview scripts and resume |
| [product-surfaces.md](references/product-surfaces.md) | ToB/ToC probe card in Discuss-S |
| [templates/briefing.md](templates/briefing.md) | Writing the freeze artifact |
| [templates/assumptions.md](templates/assumptions.md) | A standalone assumption table, linked from briefing § Falsify |
