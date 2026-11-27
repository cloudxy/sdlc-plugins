# SRE Deliver Excellence & Review Rubric

Apply alongside [deliver SKILL.md](../SKILL.md) across `06-deliver/readiness.md`, `06-deliver/checklist.md` and `incident-report.md`.

## 1. Task & Authority Boundaries

| Task / Artifact | Excellence Bar | Reject (`major` / `blocker`) |
|---|---|---|
| `deliver/prepare` (`06-deliver/readiness.md`) | Pins candidate SHA/digest, config/secret refs, gate fingerprints, N-1/N-2 compatibility, rehearsed rollback + brownout timings, SLI/SLO & runbooks; deploys nothing | Claiming deployment happened, fabricating staging rehearsals, or omitting `readiness.md` on `release_ready` |
| `deliver/checklist` (`06-deliver/checklist.md`) | Plan stays `not deployed` until `qc` opinion + release authorization; execution logs verbatim commands, timestamps, canary gates and observed health | Deploying on red/missing gates (`e2e: null` on UI), hardcoded secrets/ports, or issuing `亲爱的用户` copy (`→ ops`) |
| Solo incident (`incident-report.md`) | Mitigate-first timeline (`time-to-detect`, `time-to-recover`), direct vs systemic escape attribution, dated mechanism fixes in `.sdlc/_lessons.md` | Waiting on root-cause debugging before stopping user bleed, or person-blaming "be careful next time" items |

## 2. Recovery, Graceful Brownout & Irreversible Surfaces

- **Rehearsed rollback & dependency probes**: Code, config and compatible expand-step DB recovery state measured duration and old-code read/write compatibility. Orchestrator probes fail (`non-2xx`) when required dependencies fail, separate from human diagnostic endpoints.
- **Graceful brownout**: Runtime shed/degrade switches for heavy or failure-prone paths (AI enrichment, recommendations, large exports) are exercised on the real path before launch, proving core auth/read/checkout survives and recovers cleanly.
- **Fintech compensation-only recovery**: Never propose or run destructive `downgrade` DDL or delete/mutate committed ledger postings, settlements or audit trails; financial recovery is strictly roll-forward + reversing/compensating journal entries reconciled to zero drift with `dba`.
- **Irreversible client binary SOP (iOS / Android / Desktop / CLI / SDK / Firmware)**: Readiness verifies server-controlled feature kill-switches, minimum-supported-version floor (`426 Upgrade Required` + upgrade prompt), **N-2** backward-compatible server APIs during store phased rollout, crash-free session guardrails, and signed binary provenance.

## 3. SLI / SLO, Error Budget & Canary Discipline

- **SLI / SLO governance**: Define user-centric SLIs (journey success, P95/P99 latency, freshness), rolling SLOs, and multi-window burn-rate alerts; freeze risky feature rollouts when error budgets are exhausted unless waived in writing by an authorized human risk owner.
- **Pre-committed canary & `growth` pause signal**: Canary stages pair technical thresholds with `metrics.yaml` business guardrails in committed repo runbooks and define the exact alert/rollback signal that pauses `growth` (`06-deliver/launch.md`) traffic campaigns.
