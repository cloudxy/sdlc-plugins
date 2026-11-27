---
name: "retro"
description: "Use this skill when the spawn packet names analyst or $retro. Do NOT load in /sdlc or for writing FRs."
when_to_use: "Use this skill when the spawn packet names hat analyst or the user types $retro / names this hat. Do NOT use from parent /sdlc. Do NOT use for writing FRs or implementing pipelines."
---

# Retro — measurement plans, causal experiments, funnels, SVOT readouts

Job: **make data drive decisions without fooling ourselves** — start from "what decision does this support and what rule is pre-committed?", cite canonical **SVOT** metric definitions (`metric:<id>@v<n>`), pair every target metric with a countervailing guardrail, and match the strength of your causal claim to the actual identification design.

| Task | Approach |
|---|---|
| **Measurement plan** (`define/measurement-plan`) | Before collection or launch, write `01-define/measurement-plan.md` ([templates/measurement-plan.md](templates/measurement-plan.md)): decision + pre-committed rule, paired canonical metrics & guardrails (`metric:<id>@v<n>`), unit/population, baseline/window, event readiness (`EV-n`), and causal identification strategy (or experiment protocol when randomized). Do not force an RCT onto every operational report |
| **Post-launch readout** (`retro/readout`) | Consume `01-define/measurement-plan.md`, `<product_root>/data/metrics.yaml`, `outputs/signals-digest.md` (`ops`) and eligible data → north star / drivers / paired guardrails vs baseline → causal identifiability & refutation checks → reproducible SQL → structured `H-<n>` / `P-<n>` proposals for `pm` `apply-decisions` ([templates/retro.md](templates/retro.md)) |
| **Cycle readout** (`cycle/readout`) | Same readout method for the cycle's window and cutoff → `outputs/readout.md` (mark `interim` while the window is open; never mutate `strategy.md` directly) |
| **Independent analysis** (`retro/analyze`) | Consume question, pinned dataset snapshot descriptor and SVOT definitions → `07-retro/analysis.md` ([templates/analysis.md](templates/analysis.md)) with SVOT citations (never copy-pasted ad-hoc formulas), data health, reproducible SQL, uncertainty and refutation checks |
| **Design an A/B or switchback test** | Pre-register hypothesis, single OEC + paired guardrails, interference-safe randomization unit (user / tenant / geo-cluster / switchback), MDE/power, SRM check, and no-peeking stopping rule ([templates/experiment-design.md](templates/experiment-design.md)) |

## Gotchas

- **6-Point Data-Health Gate Before Attribution (`## 2.0 归因前数据链路健康排障门禁` — Hard Exit Rule).** Before evaluating target metrics or claiming causal/descriptive changes in `retro.md` or `analysis.md`, audit all 6 telemetry links: ① tracking version (`tracking-plan.yaml`), ② ingestion/ETL lag, ③ duplicate/missing events, ④ identity mapping (`anonymous_id ↔ user_id` / `tenant_id`), ⑤ query filters (`exclusions`), and ⑥ concurrent `sre` code/flag releases. **Hard Exit Rule**: if data-system anomalies contaminate the metric/window, tag the contaminated interval, **halt performance/causal attribution on contaminated data**, and emit a **`"Fix Data Pipeline First (`collect` / `warehouse`)"`** task instead of conclusions built on broken telemetry.
- **Cite SVOT `metric:<id>@v<n>` with Recomputable Numerator, Denominator & Time Window.** `<product_root>/data/metrics.yaml` (`warehouse`) is the Single Version of Truth ([industry-data-sops.md](../schema/references/industry-data-sops.md)). Every metric row in `retro.md` and `analysis.md` must cite `metric:<id>@v<n>` (`time_semantics`) AND display **recomputable numerator, denominator, and exact time window** so `ops`, `analyst`, and `data-warehouse-engineer` (`warehouse`) reproduce identical numbers. Propose formula updates to `pm` + `warehouse` rather than forking ad-hoc SQL.
- **Every target metric needs a paired guardrail.** Optimizing one metric in isolation invites Goodhart cannibalization: pair conversion/click lift with refund/churn/unsubscribe red lines; pair latency/cost cuts with completion/quality; pair AI automation rate with human-override/error rate ([industry-product-sops.md](../prd-gwt/references/industry-product-sops.md)).
- **State causal identifiability before claiming effect.**
  - **Randomized experiment**: run a **Sample Ratio Mismatch (SRM)** $\chi^2$ check on assigned counts BEFORE inspecting the OEC (SRM = broken routing/logging → halt interpretation!), verify SUTVA, and estimate Intent-to-Treat (**ITT**).
  - **Quasi-experiment (DID / RDD / Synthetic Control)**: test pre-treatment parallel trends, cutoff manipulation, and in-time placebos ([causal-and-funnel.md](references/causal-and-funnel.md)).
  - **Pre/post without a valid counterfactual**: causal effect is **unidentified** — write "observed change" (never "drove / caused / 归因于"), audit concurrent `sre` releases, seasonality and selection bias.
- **Marketplace, social & multi-tenant interference breaks user-level A/B tests (SUTVA violation).** When treatment and control units share scarce supply/inventory (rideshare, e-commerce stock, ad auctions), collaborate inside a B2B tenant, or interact across a social graph, user-level splits cannibalize control and bias lift (often ~2x). Choose **tenant/team randomization** (B2B), **graph-cluster / geo randomization** (social), or **Time × Geo Switchback / bipartite designs** with washout windows and cluster-robust standard errors ([experiment-design.md](references/experiment-design.md)).
- **An open window is interim; close the Seam 9 → Seam 1 loop with an explicit Feedback Intake Owner (`归口角色`).** Label open-window numbers `interim` without declaring victory. Emit structured `H-<n>` and `P-<n>` proposals naming the explicit **`归口角色` (Feedback Intake Owner)** and target Seam 1 intake (`00-discover/briefing.md` / `cycle` / `data-collector` / `data-warehouse-engineer`) for `pm` `apply-decisions`; never edit `strategy.md` directly.

## Handoff contract

Independent analysis (`retro/analyze`) consumes its pinned dataset snapshot descriptor (`workflow.py continuous dataset-capture` or provider partition/query timestamp); a running backfill never alters a pinned analysis snapshot.

| Direction | Content |
|---|---|
| **Input** | `<product_root>/data/metrics.yaml` (`metric:<id>@v<n>`) · `01-define/measurement-plan.md` · `01-define/spec.md` · `outputs/signals-digest.md` (`ops`) · `06-deliver/launch.md` · read-only replica/warehouse access |
| **Output** | `01-define/measurement-plan.md` ([templates/measurement-plan.md](templates/measurement-plan.md)) · `07-retro/retro.md` ([templates/retro.md](templates/retro.md)) · `07-retro/analysis.md` ([templates/analysis.md](templates/analysis.md)) · [templates/experiment-design.md](templates/experiment-design.md) · reproducible SQL · `H-<n>`/`P-<n>` proposals |
| **Downstream** | `pm` (`apply-decisions` & next-cycle requirements) · `growth` (next experiments referencing measurement plan) · `ops` (signal loop) |
| **Refuse** | Feature code (`→ backend`) · infra (`→ sre`) · owning canonical ETL/`metrics.yaml` pipelines (`→ warehouse`) · editing `strategy.md` · querying production OLTP primary directly |

## Self-check

- [ ] Decision and pre-committed decision rule stated upfront?
- [ ] **6-Point Data-Health Gate (`## 2.0`)** passed first — OR contaminated intervals tagged, causal/performance attribution halted, and `"Fix Data Pipeline First (collect / warehouse)"` emitted?
- [ ] Every metric row cites `<product_root>/data/metrics.yaml` (`metric:<id>@v<n>` + `time_semantics`), displays **recomputable numerator, denominator, and exact time window** (`ops` / `analyst` / `warehouse` parity), and pairs a guardrail + red line?
- [ ] Causal identifiability stated (SRM + SUTVA checked for RCT; parallel trends checked for DID; no causal claim without a counterfactual)?
- [ ] Interference structure addressed (tenant / cluster / switchback randomization used when shared supply, B2B teams or social spillovers exist)?
- [ ] Uncertainty intervals (where inferential), data-quality exclusions, and open-window `interim` labels present?
- [ ] Verbatim reproducible SQL + pinned dataset snapshot included, read-only store used, zero PII exposed, and `H-<n>`/`P-<n>` proposals name explicit **Feedback Intake Owner (`归口角色`)** feeding into Seam 1 (`00-discover` / `cycle`) without editing `strategy.md`?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [causal-and-funnel.md](references/causal-and-funnel.md) | Causal identifiability ladder, DID parallel trends, selection bias, Simpson's paradox, funnels & cohorts |
| [experiment-design.md](references/experiment-design.md) | Pre-registered OEC + paired guardrails, SRM check, tenant/cluster/switchback interference designs, MDE & no-peeking |
| [industry-product-sops.md](../prd-gwt/references/industry-product-sops.md) | Domain metric-guardrail pairs (marketplace liquidity, fintech risk, SaaS retention, AI override rates) |
| [industry-data-sops.md](../schema/references/industry-data-sops.md) | SVOT metric governance, point-in-time cohorts, and analytical reproducibility |
| [templates/measurement-plan.md](templates/measurement-plan.md) | Pre-launch measurement & identification plan (`01-define/measurement-plan.md`) |
| [templates/analysis.md](templates/analysis.md) | Independent / funnel / diagnostic readout (`07-retro/analysis.md`) |
| [templates/experiment-design.md](templates/experiment-design.md) | Pre-registered A/B, cluster or switchback experiment protocol |
| [templates/retro.md](templates/retro.md) | Post-launch readout with reproducible SQL & `H-<n>`/`P-<n>` proposals (`07-retro/retro.md`) |

> Experiment discipline from: `anthropics/skills@41bbe19` (doc-coauthoring SKILL.md multi-stage workflow pattern, 2026-09-03)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
