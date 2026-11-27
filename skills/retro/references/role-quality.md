# Analyst Retro & Experimentation Excellence Rubric

Apply alongside [retro SKILL.md](../SKILL.md) across `01-define/measurement-plan.md`, `07-retro/analysis.md`, `07-retro/retro.md`, `outputs/readout.md` and `experiment-design.md`.

## 1. Decision-First & SVOT Governance

| Deliverable | Excellence Bar | Reject (`major` / `blocker`) |
|---|---|---|
| `define/measurement-plan` (`01-define/measurement-plan.md`) | Names the governed decision + pre-committed threshold, cites SVOT `metric:<id>@v<n>` + paired guardrails, verifies `EV-n` readiness and selects a right-sized identification method | Forcing RCTs onto simple operational reports, inventing metrics outside `metrics.yaml`, or omitting guardrails |
| `retro/analyze` (`07-retro/analysis.md`) | Cites `metric:<id>@v<n>` + `time_semantics`, pins read-only dataset snapshot, reports denominators + CIs, runs refutation checks and includes verbatim SQL | Copy-pasting/forking metric formulas in prose, querying live OLTP primaries, or exposing PII (`< 5` user cells) |
| `retro/readout` (`07-retro/retro.md` · `outputs/readout.md`) | Compares pre-committed targets vs actuals, marks open windows `interim`, incorporates `outputs/signals-digest.md`, and emits `H-<n>`/`P-<n>` proposals | Claiming causation from pre/post without counterfactual, peeking OEC early, or editing `strategy.md` directly |

## 2. Paired Guardrails, Causal Identifiability & Interference

- **Paired metric-guardrail**: Every primary/driver metric is paired with at least one countervailing guardrail and a pre-committed red-line threshold (e.g. conversion lift paired with refund/unsubscribe rate; latency/cost cuts paired with accuracy/completion; AI automation rate paired with human-override/error rate).
- **Explicit causal identifiability**: State identification assumptions before interpreting numbers:
  - **Randomized experiments**: verify pre-treatment AA balance and **Sample Ratio Mismatch (SRM)** $\chi^2$ BEFORE reading OEC (SRM halts readout!), analyze **Intent-to-Treat (ITT)**, and forbid OEC peeking before planned sample/duration.
  - **Quasi-experiments (DID / RDD / Synthetic Control)**: test pre-treatment parallel trends, cutoff manipulation and in-time placebos.
  - **Observational pre/post**: strictly **unidentified** causal effect — report observed changes only (never "drove / caused / 归因于") and test seasonality, concurrent `sre` releases, Simpson's paradox and pre-launch user selection bias.
- **Marketplace, social & multi-tenant interference (SUTVA)**: Reject naive user-level randomization when units share scarce supply/inventory, B2B workspaces or social graphs; require **tenant/team randomization**, **geo/graph-cluster randomization**, or **Time × Geo Switchback** designs with washout windows and cluster-robust standard errors.
