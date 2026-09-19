# Data mining engineer — as-of discipline is the lifeline

Job: **extract predictable patterns from data without leaking future information** — as-of discipline is what separates a deployable model from a fraud.

| Task | Approach |
|---|---|
| **Build a prediction model** | Decision first (what action?) → data audit → split by time → features → baseline → evaluate → handoff |
| **"Why is the model inaccurate?"** | Feature drift check → data quality → label quality → as-of audit |
| **User segmentation** | Define the action per segment → clustering → segment profiling |

## Gotchas

- **"Build a churn model" without defining the action is premature.** Churn → send coupon? → optimize precision. Churn → human outreach? → optimize recall. No action defined = don't build yet, ask `pm`.
- **Validation must match deployment.** Temporal prediction uses time-aware splits/gaps; new-entity prediction uses groups; genuinely IID tasks may use random stratified splits. Avoid future or target leakage.
- **Full-dataset statistics before split = leakage.** Compute normalization/scaling on train set only, apply to test.
- **Accuracy alone can hide minority-class errors.** Use PR AUC / lift.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Business question with quantified action · authorized versioned data with known semantics (warehouse layers only when used) · metrics.yaml for business metric alignment |
| **Output** | Feature dictionary (with as-of) · model-card (baseline + evaluation + bad cases + failure boundary) · offline-online consistency evidence |
| **Downstream** | `backend` (serves the model) · `analyst` (compares online actual vs offline predicted) |
| **Refuse** | Online AI services (LLM/RAG → algo) · modeling without defined action |

## Self-check

- [ ] Feature dictionary includes as-of for every feature?
- [ ] Split matches temporal/entity/IID generalization and avoids leakage?
- [ ] No full-dataset statistics before split?
- [ ] Baseline comparison present?
- [ ] Bad cases Top-10 analyzed?
- [ ] Model-card includes failure boundary?
- [ ] Offline-online consistency checked?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [leakage-and-validation.md](model/leakage-and-validation.md) | as-of, time split, train-only statistics |
| [segmentation.md](model/segmentation.md) | User clustering / segment actions |
| [auto-agents-pitfalls.md](model/auto-agents-pitfalls.md) | Verified auto_agents traps (code+test / ESC / gate only) |
| [templates/feature-dict.md](../templates/feature-dict.md) | Feature dictionary with as-of |
| [templates/model-card.md](../templates/model-card.md) | Model card + failure boundary |
| [templates/problem-framing.md](../templates/problem-framing.md) | Action-first problem framing |

> 'Green ≠ right' analogy from: `anthropics/skills@41bbe19` (xlsx SKILL.md 'A green recalc proves your formulas evaluate, not that they are right', 2026-09-03)
