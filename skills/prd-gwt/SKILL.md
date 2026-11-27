---
name: "prd-gwt"
description: "Use when shaping product value, journeys, PRD/GWT, metrics or PM acceptance. In sdlc-workflow:pm or $prd-gwt. Do NOT load in /sdlc or for schema/code."
when_to_use: "Use when shaping core value and journeys, writing or judging a PRD, GWT, RICE, metrics blueprint, or walking PM acceptance on the build. Load inside sdlc-workflow:pm, or $prd-gwt. Do NOT use while /sdlc is running in this window. Do NOT use for architecture, schema, or implementation."
---

# PRD / GWT / metrics — product definition procedure

Procedure for product definition and PM acceptance. The `sdlc-workflow:pm` agent owns identity and refuse list. Solo entry: `$prd-gwt`. Reviewers and qc load it to judge specs.

Job: **decide what is worth building, make its core value unmistakable, and make every requirement testable and measurable.** Two questions gate every requirement — "does it move the core value path?" and "how will we know it worked?" — and one more gates the release: "does the build actually deliver it?"

| Task | Approach |
|---|---|
| **New feature, briefing frozen** | Read product layer + `project_profile` ([industry-product-sops.md](references/industry-product-sops.md)) → JTBD + core value path → credible alternatives for unresolved choices ([product-shaping.md](references/product-shaping.md)) → journeys J-n → FR/GWT (or probabilistic eval bounds for AI) → NFR → paired metrics + tracking → scope |
| **No briefing on an L2+ change** | Identify missing decisions; reuse an approved customer brief or existing spec. Request discover only for consequential unresolved value/scope questions |
| **Product layer missing or unfilled** | Fill `strategy.md` + `feature-map.md` from evidence first ([templates/product-strategy.md](templates/product-strategy.md), [templates/feature-map.md](templates/feature-map.md)); mark inferences `[推断]` |
| **"What are the core features?"** | Core value path + the removal test + Kano layering in `feature-map.md` ([product-shaping.md](references/product-shaping.md)) |
| **"Is this worth building?" / prioritize** | Triage + value-path contribution + RICE ([requirement-triage.md](references/requirement-triage.md)) |
| **Review a PRD** | Self-check below, every item |
| **Scope too big** | Appetite slicing along the journey: keep the path to Aha, cut around it |
| **Stage `accept`** | Walk J-n on the build ([acceptance-walkthrough.md](references/acceptance-walkthrough.md)) → `04-verify/accept-pm.md` ([templates/accept-pm.md](templates/accept-pm.md)) |
| **Frozen FRs change** | Re-triage + `superseded` annotation (numbering discipline) |
| **Product cycle decisions** (`cycle/apply-decisions`) | Decide every proposal of the cycle (signals, readout, experiments) in `outputs/decisions.md` ([templates/cycle-decisions.md](templates/cycle-decisions.md)); apply accepted changes to strategy.md / feature-map.md within `product_writes`; reference `SIG-…` ids, never edit the signal store; strategic calls stay 待确认 until the operator answers |

## Refinement and handoff

Detail the current feature/slice, keeping future product capabilities coarse. Separate business decomposition (journeys, rules, permissions, states, boundaries, observable acceptance) from implementation tickets owned by architecture after the necessary design/technical choices. An exploratory prototype or feasibility result may expose missing requirements before handoff. Accepted means ready for the named consumers at this version, not immutable forever. On feedback, state the quality gap, revise only the affected scope, preserve stable requirement IDs and return downstream impact. A draft and an accepted handoff have different completion claims.

When the user cannot express a need or revises it during discussion, use the shared [discussion protocol](../discover/references/discuss-protocol.md). In a delegated task, return consequential questions, credible options and blocked consumers to the manager; solo entry can discuss directly. Reuse known answers. Examples can help a preference form; record it as a decision with authority, separately from evidence of effectiveness.

## Gotchas — things that go wrong without being told

- **A feature request may hide an unclear goal.** When purpose is unresolved, explore context/current behavior/desired progress. When the request is already understood and authorized, preserve it rather than repeating the probe.
- **A requirement list is not a product.** Without the core value path, every FR looks equally important and the team polishes the periphery. Rank by contribution to the path; label peripheral work as peripheral.
- **Do not reopen settled choices.** Compare credible concepts for unresolved decisions; cite existing authorization when scope is already clear. Never invent alternatives to meet a quota.
- **Journeys make value testable.** A spec without walkable journeys J-n leaves qa with unit-level mappings and acceptance with nothing to walk; the build passes tests and is still unusable.
- **"正确的", "合理的", "友好的", "体验良好", "稳定及时", "gracefully" are untestable.** `qa` cannot write a case from "handle errors appropriately". Structure every acceptance row as `前提(Given) — 操作(When) — 预期结果(Then) — 判定标准`; when genuinely qualitative (visual/copy), declare explicit **`判定依据 + 判定人`** (e.g., `designer` via `accept-design.md`) — vague words remain strictly banned.
- **0→1 has no tickets or data.** Do not block on missing E2 evidence and do not fake it: write hypotheses with the cheapest validation and the metric that will settle them.
- **RICE is a ranking heuristic, not a probability model.** Record source, scope and uncertainty; no evidence does not imply a measured 50% confidence.
- **Measurement needs an available source.** Reuse logs, operational facts or canonical metrics where sufficient; request new events through `collect` only for identified gaps.
- **"The system provides batch export" is system-speak.** Write "the support lead can export all open tickets in one action".
- **Never commit to a delivery date.** Appetite is a budget, not a schedule.
- **Safety, permissions and data consistency are never cut for appetite.**
- **Same preconditions and action must have compatible outcomes.** Two FRs about the same screen must not disagree; NFR one-liners must match the permission matrix and metrics blueprint.
- **Falsifiability + YAGNI/KISS.** Every hypothesis and requirement states what observable outcome proves it wrong. Cut speculative "future extensibility" or multi-tenant/config knobs with no current consumer (`支持扩展` without a concrete second case is deleted).
- **SSOT & SVOT — cite, never copy-paste.** Domain terms cite `<product_root>/domain-model.md §2` (propose new terms as deltas for `dba`); status-quo and market evidence cite `00-discover/compete.md`, `00-discover/market.md` and `SIG-<yyyymm>-<n>` IDs instead of re-narrating 4 times; metrics cite `metric:<id>@v<n>` in `data/metrics.yaml` instead of pasting SQL/formulas into `spec.md` (net-new metrics carry a proposal stub handed off to `data-warehouse-engineer`).
- **Probabilistic AI ≠ fake 100% deterministic GWT.** On `ai-agentic` / `ai-enabled` surfaces ([industry-product-sops.md](references/industry-product-sops.md)), write deterministic GWT only for the system envelope (permissions, schema, citation links, timeout/fallback, HITL confirmation, cost cap) and specify golden-eval pass thresholds, hallucination/abstention bounds and token COGS guardrails for open-ended model outputs.
- **Consequential choices need authority.** Audience, positioning, value, pricing, launch, north star and scope cuts need the operator's decision. Business details can also be consequential: duplicate/overwrite semantics, access or ownership rules must not become defaults merely because they are called operational. Reuse accepted rules; otherwise return Q-* with options, recommendation, decision owner and blocked FRs. Apply defaults only to reversible details within existing authority that do not settle an unresolved business outcome; label them 默认 with reasons. Silence is not consent.

## Key decisions

### Core value path and core features

```
who → trigger → key action(s) → Aha (sees/gets what) → reason to return
```

A feature is **core** if removing it stops users reaching Aha. Everything else is **support** (makes core usable/sellable: accounts, permissions, billing), **growth** (spreads or converts value), or **experience** (reduces friction). Tag Kano type too (must-be / performance / attractive / indifferent). Keep this in `feature-map.md`; the spec says where this feature sits on the path and which of *faster / stronger / more often / more people* it improves.

### Working backwards — the problem & admission anchors

Capture who, current situation, desired outcome and how improvement can be observed. Carry forward from `briefing.md` into `spec.md` §1 both the **System/Data-Linkage Anchor** (`对应系统模块 / 数据链路落点`: `product_root/architecture.md` module, `domain-model.md` entity or `tracking-plan.yaml` pipeline; `greenfield` for net-new 0→1) and the **Data Availability Tri-State** (`数据已证实 | 数据证伪（终止） | 数据不可用，需先立项补埋点 EV-n`). Keep unknown costs/baselines explicit; never fabricate telemetry numbers.

### Bidirectional non-orphan traceability (`Goal/Metric ↔ Journey J-n ↔ FR-n ↔ GWT`)

For unresolved choices, compare concepts on job coverage, value-path contribution, observable value, alternatives, rough cost (`architect` input) and risk. Map activities from trigger to outcome, slice a usable path, and write key journeys `J-n` (action → observable result → `FR-n`). Bind every FR header upward (`### FR-01 <能力>（旅程：J-1 第 1 步｜挂靠目标：<metric:<id>@v<n> 或假设 A-n>）`) and downward to 4-part acceptance (`前提(Given) — 操作(When) — 预期结果(Then) — 判定标准`). **PRD Exit Gate:** zero orphan FRs without a parent goal/metric (`防镀金`) and zero FRs without verifiable GWT/eval rows; headless work need not invent screens.

### RICE scoring

`RICE = (Reach × Impact × Confidence) / Effort`. Reach from data; Impact 3/2/1/0.5/0.25; Confidence uses explicitly documented local ranking weights and uncertainty, not universal probability buckets; Effort from architect. RICE ranks; it does not decide — compliance may be mandatory, value-path work may outrank a higher score.

### NFR checklist

Performance · Capacity · Availability · Security · Permissions · Compliance · Compatibility · Observability · i18n · Maintainability. Each testable, or explicit `N/A` with a reason.

### Metrics blueprint — 4 mandatory goal elements & counter-guardrails (SVOT)

Select relevant success and guardrail metrics without an arbitrary count quota ([metrics-blueprint.md](references/metrics-blueprint.md)). Every business goal row in `spec.md` §8 must specify **4 mandatory elements**: **`指标定义（SVOT metric:<id>@v<n>）· 统计范围 · 基线值（缺基线必填：待补责任人与补齐时间，禁含糊略过）· 目标值`**, paired with a **counter-guardrail** catching gaming or collateral damage (conversion ↔ refund/churn, AI speed ↔ acceptance/token COGS, notification CTR ↔ opt-out/uninstall). PM owns business meaning, scope, baseline and acceptance/redline thresholds; `data-warehouse-engineer` owns canonical calculation formulas in `data/metrics.yaml`. Cite `metric:<id>@v<n>` in `spec.md` rather than restating formulas; hand off net-new metric proposals to `data-warehouse-engineer` and event gaps (`EV-n`) to `data-collector` via `01-define/tracking.md`.

### Scope cutting with appetite

Budget first, scope follows. Cut **around** the path to Aha, not through it: by role → scenario → volume → automation → format. Cut items go to Out of Scope with "next round / won't do". Exceeding appetite by 50% → stop and re-judge.

## Source and authority

PM may sketch to clarify business intent, but final UI decisions live in the design contract. Spec is the canonical business behavior source; tickets/tests cite IDs and revision. A detected implementation constraint triggers architecture change-impact and the affected owner, not unilateral acceptance reduction. Product baseline status distinguishes proposed, implemented and deployed work.

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
- [ ] credible alternatives for unresolved choices compared; the choice and the losers' reasons recorded?
- [ ] Key journeys J-n are walkable step tables with a success standard; every FR anchors to a step?
- [ ] Growth's highlight hypotheses reflected as moments in a journey (or explicitly rejected)?
- [ ] Hypotheses labelled with validation method and metric (no fake E2+)?

**Specification & Exit Gate:**
- [ ] §1 carries forward `对应系统模块 / 数据链路落点` and Data Availability Tri-State from `briefing.md`?
- [ ] **Bidirectional non-orphan exit gate:** zero orphan FRs without a parent `metric:<id>@v<n>` / `A-n` (`防镀金`) and zero FRs without verifiable 4-part GWT/eval rows (`Goal/Metric ↔ J-n ↔ FR-n ↔ GWT`)?
- [ ] Each FR covers applicable success, failure, permission and state risks via `前提(Given) — 操作(When) — 预期结果(Then) — 判定标准`; qualitative criteria state `判定依据 + 判定人` with zero vague words (`体验良好`, `稳定及时`, `友好的`, `gracefully`)?
- [ ] Identical preconditions/actions have compatible outcomes; NFR/matrix/blueprint agree with FRs?
- [ ] State-dependent FRs list legal and illegal transitions?
- [ ] NFR walked through all 10 categories?
- [ ] No technical decisions made for downstream?

**Metrics & scope:**
- [ ] Every goal metric in §8 states all 4 mandatory elements (`指标定义 metric:<id>@v<n> · 统计范围 · 基线值（缺基线必填责任人与补齐时间）· 目标值`) + paired counter-guardrails?
- [ ] `tracking.md` written (tracking: yes) or `埋点：N/A（理由）`?
- [ ] Appetite declared; out-of-scope listed; security/permissions/consistency not cut?
- [ ] Open decisions cite owner, recommendation and blocked scope; already authorized decisions are reused?
- [ ] Product layer updated (`strategy.md` / `feature-map.md`) and the delta row returned (the manager records it)?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [industry-product-sops.md](references/industry-product-sops.md) | Matching `project_profile` (`b2b-saas`, `fintech-ledger`, `ecommerce-marketplace`, `consumer-social`, `ai-agentic`, `aigc-workbench`, `data-crawler`, `regulated-compliance`, `client-iot-localfirst` + traits) |
| [spec-task.md](references/spec-task.md) | Assigned define/spec: input sufficiency, authorized short paths and task completion |
| [product-shaping.md](references/product-shaping.md) | Before any FR: JTBD, core value path and Aha, removal test + Kano, opportunity–solution tree, MVP skeleton, 0→1 hypothesis mode |
| [requirement-triage.md](references/requirement-triage.md) | Triaging requirements, digging for the real problem behind solution-speak, RICE |
| [discussion protocol](../discover/references/discuss-protocol.md) | Unclear needs, inability to answer, rejected options, goal changes and scoped readiness |
| [gwt-authoring.md](references/gwt-authoring.md) | Writing GWT, fixing untestable words, enumerating edge cases, one-oracle rule |
| [flow-diagram.md](references/flow-diagram.md) | Packet visuals flow/state: drawing a checked business flow or state diagram from the spec |
| [metrics-blueprint.md](references/metrics-blueprint.md) | Designing metrics and instrumentation gaps |
| [acceptance-walkthrough.md](references/acceptance-walkthrough.md) | Stage accept: walking journeys on the build, severity, verdict |
| [templates/spec.md](templates/spec.md) · [templates/user-story.md](templates/user-story.md) | Writing the spec / lightweight stories |
| [templates/product-strategy.md](templates/product-strategy.md) · [templates/feature-map.md](templates/feature-map.md) | Bootstrapping or updating the product layer |
| [templates/accept-pm.md](templates/accept-pm.md) | Writing `04-verify/accept-pm.md` |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
