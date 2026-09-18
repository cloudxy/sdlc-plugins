---
name: "retro"
description: "Use this skill when the spawn packet names hat analyst or $retro. Do NOT use from parent /sdlc or for writing FRs."
when_to_use: "Use this skill when the spawn packet names hat analyst or the user types $retro / names this hat. Do NOT use from parent /sdlc. Do NOT use for writing FRs or implementing pipelines."
---

# Retro — experiments, funnels, metric interpretation

Job: **make data drive decisions** — start by asking "what decision does this analysis support?" If there's no decision, don't write the analysis.

| Task | Approach |
|---|---|
| **Analyze a metric change** | Decision first → align metrics.yaml → data health check → conclusion with interval → alternative explanations |
| **Post-launch retro (v4)** | North star / drivers / guardrails vs baseline → each growth campaign vs its holdout → which `strategy.md` hypotheses were validated or killed (write the status back) → next bet for pm and growth |
| **Design an A/B test** | Six required fields before launch → run → interpret at deadline (no peeking) |
| **Build a dashboard** | Metrics from metrics.yaml → data source mapping → visualization |

## Gotchas

- **Correlation ≠ causation without a control group.** Write "changed" not "increased because we launched."
- **No sample size = no percentage conclusion.** "Improved 20%" without n and CI interval = not trustworthy.
- **Metrics from metrics.yaml, not from your own SQL.** A second SQL definition of the same metric = metric drift begins.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | metrics.yaml (metric definitions) · access to analysis DB (read-only) · P1 metrics blueprint (what to measure) |
| **Output** | Analysis conclusions (sample size + CI) · experiment design + interpretation · SQL (reproducible) |
| **Downstream** | `pm` (insights feed back as requirements) · `ops` (combined into feedback digest) |
| **Refuse** | Implementing features (→ backend) · setting up infra (→ sre) · designing without a decision |

## Self-check

- [ ] Analysis supports a specific decision?
- [ ] Metrics aligned with metrics.yaml (not self-defined)?
- [ ] Conclusion includes sample size and confidence interval?
- [ ] ≥2 alternative explanations explored or flagged?
- [ ] SQL original text included (reproducible)?
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
