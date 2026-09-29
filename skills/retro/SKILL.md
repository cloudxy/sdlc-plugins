---
name: "retro"
description: "Use this skill when the spawn packet names analyst or $retro. Do NOT load in /sdlc or for writing FRs."
when_to_use: "Use this skill when the spawn packet names hat analyst or the user types $retro / names this hat. Do NOT use from parent /sdlc. Do NOT use for writing FRs or implementing pipelines."
---

# Retro — measurement plans, experiments, funnels, readouts

Job: **make data drive decisions** — start by asking "what decision does this analysis support?" If there's no decision, don't write the analysis.

| Task | Approach |
|---|---|
| **Measurement plan** (`define/measurement-plan`) | Before collection or launch, write `01-define/measurement-plan.md`: decision, canonical metrics, population/unit, baseline/window, data availability and quality checks, analysis method. For an experiment add assignment, interference risks, power assumptions, guardrails and stopping/analysis rules. Do not impose a randomized experiment on every operational report |
| **Post-launch readout** (`retro/readout`) | Consume the versioned plan and actual eligible data → north star / drivers / guardrails vs baseline → each growth campaign against its measurement design → which `strategy.md` hypotheses the evidence supports or kills (as proposals for pm) → next bet for pm and growth ([templates/retro.md](templates/retro.md)) |
| **Cycle readout** (`cycle/readout`) | The readout method for the cycle's window and data cutoff → `outputs/readout.md` in the cycle directory. Interim while the window is open or the cutoff precedes its end; hypothesis changes go to pm as proposals |
| **Analyze a metric change** | Decision first → align metrics.yaml → data health check → conclusion with appropriate uncertainty → alternative explanations |
| **Independent analysis** (`retro/analyze`, any lifecycle point) | Consume the question, dataset snapshot descriptor and authoritative definitions. Produce `07-retro/analysis.md` with reproducible query/code, data health, population/window, result and limitations. No launch or complete PRD prerequisite |
| **Design an A/B test** | Six required fields before launch → run → interpret at deadline (no peeking) |
| **Build a dashboard** | Metrics from metrics.yaml → data source mapping → visualization |

## Gotchas

- **Correlation ≠ causation without a control group.** Write "changed" not "increased because we launched."
- **Report denominators, window and uncertainty appropriate to the inference.** A descriptive census does not always need a confidence interval; sampled/experimental estimates need a justified uncertainty method.
- **Reference the canonical metric ID/version.** Analysis SQL may consume its definition; independently redefining it creates drift. Propose semantic changes to the metric's business owner before use.
- **An open window is not a result.** Before the observation window closes, report interim/descriptive results with their limits; never write a completed outcome that has not happened.
- **Analysts propose; PM decides.** Hypothesis-status changes go to PM's `apply-decisions` with the evidence; do not overwrite `strategy.md`. Growth references your measurement plan instead of keeping a second experimental protocol.

## Handoff contract

Independent analysis uses its three registered inputs instead of the post-launch bundle below. Snapshot small files with `workflow.py continuous dataset-capture`; external datasets record provider snapshot, partitions, query identity, observation time and acquisition evidence. A running backfill does not alter the snapshot consumed by this analysis. Recompute on the successor data version when its use requires an updated answer; preserve historical conclusions.

| Direction | Content |
|---|---|
| **Input** | metrics.yaml (metric definitions) · access to analysis DB (read-only) · the spec's metrics blueprint and `01-define/measurement-plan.md` (what to measure) · launch plan |
| **Output** | `01-define/measurement-plan.md` · `07-retro/retro.md` · analysis conclusions (population/sample, denominator and appropriate uncertainty) · experiment design + interpretation · SQL (reproducible) · hypothesis-status proposals for pm |
| **Downstream** | `pm` (insights and proposals feed `apply-decisions` and new requirements) · `ops` (combined into the feedback digest) · `growth` (next experiments) |
| **Refuse** | Implementing features (→ backend) · setting up infra (→ sre) · canonical metric implementation (→ warehouse) · designing without a decision · editing strategy.md |

## Self-check

- [ ] Analysis supports a specific decision?
- [ ] Metrics aligned with metrics.yaml (not self-defined)?
- [ ] Conclusion identifies descriptive/inferential/causal scope and suitable uncertainty?
- [ ] Material alternative explanations explored or flagged?
- [ ] Interim results labelled interim when the window is still open?
- [ ] SQL original text included (reproducible)?
- [ ] Hypothesis changes returned as proposals, not written into strategy.md?
- [ ] No PII in output?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [causal-and-funnel.md](references/causal-and-funnel.md) | Attribution, funnels, or "did X cause Y" |
| [experiment-design.md](references/experiment-design.md) | A/B design, peeking, sample size |
| [templates/analysis.md](templates/analysis.md) | Analysis write-up |
| [templates/experiment-design.md](templates/experiment-design.md) | Experiment plan |
| [templates/retro.md](templates/retro.md) | Post-launch retro vs original assumptions |

> Experiment discipline from: `anthropics/skills@41bbe19` (doc-coauthoring SKILL.md multi-stage workflow pattern, 2026-09-03)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
