---
name: "deliver"
description: "Use this skill when the spawn packet names sre or $deliver. Do NOT load in /sdlc or for business code."
when_to_use: "Use this skill when the spawn packet names hat sre or the user types $deliver / names this hat. Do NOT use from parent /sdlc. Do NOT use for business feature code or OLTP schema."
---

# Deliver — 运维的发/回/看（不是产品运营）

This is **SRE / 运维** on hat `sre`. User-facing announcements, support scripts, and ticket aggregation belong to `ops` (产品运营). Do not write 亲爱的用户 copy here.

Job: **make deployment boring, degradation graceful, and recovery deterministic** — SLI/SLO error budgets govern release velocity, rollback and brownout paths are rehearsed on real paths, financial ledgers recover strictly by compensation, irreversible client binaries ship with kill-switches and N-2 server compatibility, and configuration lives outside code.

| Task | When | Approach |
|---|---|---|
| **Prepare** (`deliver/prepare`) | Before `qc`, for `release_ready` / `deployed` targets | Write `06-deliver/readiness.md` ([templates/readiness.md](templates/readiness.md)): artifact/config identity, gate fingerprints, DB & N-2 API compatibility, rehearsed rollback/brownout/compensation boundaries, SLI/SLO & canary thresholds, committed runbooks and operator ownership. Deploys nothing |
| **Release checklist — plan** (`deliver/checklist`) | User asked for a plan, or deployment is not authorized | [templates/release-checklist.md](templates/release-checklist.md) with status `not deployed` |
| **Release checklist — execute** (`deliver/checklist`) | After scoped `qc` opinion, within existing release authorization | Pre-deploy fingerprints → deploy steps → dependency-aware health + consumer check → rollback/brownout readiness → canary & SLO burn watch; record environment, version, commands, timestamps and observed health |
| **CI wiring** (`deliver/ci`) | Pipeline wiring changes | Primary skill `sdlc-workflow:cicd` (`06-deliver/ci.md`) |
| **Log analysis** (`deliver/log-analysis`) | Log parsing, schema inference, error clustering, spike triage | Strictly read-only: run `python3 <PLUGIN_ROOT>/scripts/tools/log_profiler.py <log>` to profile lines/JSON keys/error signatures, redact secrets, and write `04-verify/log-analysis.md` |
| **Read-only ops diagnosis** (`deliver/ops-diagnose`) | Service OOM, 5xx, latency, Docker/K8s/alerting diagnosis via `/sdlc` | Strictly read-only diagnosis & mitigation/runbook plan (`04-verify/ops-diagnosis.md`); **zero unauthorized production mutations** (executing prod mitigation/restart/rollback still requires explicit operator authorization) |
| **"This is down"** | Solo `$deliver` or authorized post-triage incident follow-up (requires operator authorization for every prod action) | Four-phase response: mitigate/recover → preserve timeline → root cause → blameless postmortem ([templates/incident-report.md](templates/incident-report.md)) |
| **SLI / SLO & alerts** | Prepare / checklist monitoring section, or solo | User-centric SLIs → rolling SLOs & Error Budget burn-rate alerts → committed runbooks ([observability-and-incident.md](references/observability-and-incident.md)) |
| **Capacity & brownout review** | When traffic, dependencies or AI/compute costs change | `architecture.md` capacity model + `06-deliver/launch.md` traffic → bottleneck & graceful brownout verification |

## Gotchas

- **Toolchains, target architecture and lockfile behavior are platform-specific.** Inspect pinned versions and validate builds on the target CI/production architecture (`x86_64` vs `arm64`); a green local macOS build proves nothing about Linux container resolution.
- **Identify port/process ownership before acting.** Prefer graceful service stop via its service manager; never kill an unrelated process to make a check green, and scope network/git workarounds to the affected command rather than mutating global user config.
- **Deploy ≠ Release via Feature Flags.** Deploy code **dark** (feature flag default `OFF` in production); control progressive user exposure (`flag → canary → ring`) separately from container/binary deployment so a **runtime `kill switch` disables exposure in seconds without redeployment**.
- **SLI / SLO, 24-Hour Window & Statistical Quadruple Circuit Breakers govern rollout.** Define user-facing SLIs (critical-journey success rate, P95/P99 latency, data freshness — never host CPU alone) and enforce a **minimum 24-hour observation window** guarded by the **statistical quadruple**: ① error rate `> baseline + 3σ` for `2 min`, ② P95 latency `> 150%` SLO for `3 min`, ③ error-budget burn rate `> 5×` historical mean, or ④ core business metric (`metric:<id>@v<n>`) sudden drop. Hitting any one triggers **automatic rollout halt, change freeze, one-click rollback/kill-switch, alert push, and forensic snapshot preservation**. When error budget is exhausted, freeze non-essential feature rollouts unless an authorized human risk owner signs an explicit waiver.
- **6 Executable Runbook Fields & Staging Rollback Execution Proof.** Every Runbook / `release-checklist.md` / `readiness.md` must contain all **6 executable fields**: ① pre-deploy checklist, ② copyable deploy steps, ③ progressive `flag/canary/ring` rollout, ④ health signals, ⑤ explicit stop/rollback triggers, and ⑥ rollback target + verified executor permission + exact command/console path + measured expected duration + rollback-failure fallback. **Hard rule: 只在文档写未在 staging 实测执行 = 无回滚路径 = 阻塞放行.**
- **Graceful brownout must be exercised on the real path.** Before `release_ready`, toggle brownout switches in a safe environment to confirm non-core load (AI enrichment, recommendations, heavy exports) sheds cleanly while core auth/read/checkout stays healthy and recovers without restart.
- **Fintech & accounting ledgers use compensation-only recovery — never `downgrade`.** Never run destructive `downgrade` DDL or delete/update committed ledger postings, payment settlements or audit trails. Financial and irreversible side-effect recovery is strictly **roll-forward + reversing/compensating journal entries** reconciled to zero drift with `dba` (`schema`). See [industry-delivery-sops.md](../impl-evidence/references/industry-delivery-sops.md).
- **Client binaries (iOS / Android / Desktop / CLI / SDK / Firmware) are irreversible once shipped.** You cannot container-rollback a binary on a user's device or bypass App Store review latency. Require before shipping: (1) server-controlled **feature kill-switches**, (2) **forced-upgrade / minimum-version floor** (`426 Upgrade Required` or version-manifest gate with upgrade UI), (3) **N-2 backward-compatible server APIs** across active client versions, (4) crash-free session guardrails, and (5) signed binary provenance.
- **Orchestrator health probes must fail (non-2xx) when a required dependency fails**, while staying separate from verbose human diagnostic endpoints.
- **Runbooks and postmortems live in committed repo paths** — never in gitignored directories.

## Key decisions

### Release & readiness discipline ([release-and-rollback.md](references/release-and-rollback.md))

1. **Gate fingerprints & Deploy ≠ Release**: exact candidate SHA + verbatim command + exit code (`test`, `lint`, `build`, `migration`, `e2e` — UI changes never allow `e2e: null`), plus dark-deploy Feature Flag & `kill switch` wiring.
2. **Compatibility & irreversible surfaces**: expand-contract N-1 DB coexistence; compensation-only ledger plan when money/postings exist; kill-switch + forced-upgrade floor + N-2 API compatibility for native/desktop/SDK releases.
3. **6-Field Runbook, Staging Rollback Proof & Graceful Brownout**: verify all 6 executable Runbook fields, record **actual staging rollback execution proof** (measured timing + rollback-failure fallback; unexecuted prose blocks `release_ready`), and verify brownout toggles.
4. **24h Canary & Statistical Quadruple Breakers**: progressive `flag/canary/ring` rollout (`1% → 10% → 50% → 100%`, `≥ 24h` observation window) wired to the 4 statistical circuit breakers (error `> baseline + 3σ` for `2m`, P95 `> 150%` SLO for `3m`, burn `> 5×` mean, or business metric cliff → auto-halt, freeze, one-click rollback, alert & forensics), plus the pause signal `growth` (`06-deliver/launch.md`) must obey.

### Incident response (four phases)

1. **Triage & safe mitigation**: stop user bleed first (rollback if data-compatible, feature kill-switch, brownout shed, rate limit) — never delay mitigation to finish root-cause debugging.
2. **Timeline**: capture timestamps immediately (`time-to-detect`, `time-to-recover`) while preserving logs/forensics.
3. **Root cause & escape attribution**: separate direct trigger from systemic gate escape (`需求缺陷` vs `环境/流程逃逸`).
4. **Blameless postmortem**: record owned, dated mechanism fixes in `.sdlc/_lessons.md`.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Accepted delivery target + `02-shape/contract.md` / `db-spec.md`; `prepare` feeds `qc`, `execute` consumes `qc` `release-opinion.md` |
| **Output** | `06-deliver/readiness.md` ([templates/readiness.md](templates/readiness.md)) · `06-deliver/checklist.md` ([templates/release-checklist.md](templates/release-checklist.md)) · `04-verify/log-analysis.md` (`deliver/log-analysis`) · `04-verify/ops-diagnosis.md` (`deliver/ops-diagnose`) · solo incident reports ([templates/incident-report.md](templates/incident-report.md)) |
| **Downstream** | Runtime facts → `ops` (`enablement` / `signals`) — **never** user-facing announcements from `sre` · postmortems → `.sdlc/_lessons.md` |
| **Refuse** | Business feature code (`→ backend`/`frontend`) · OLTP schema policy (`→ dba`) · `亲爱的用户` announcements / CS scripts (`→ ops`) · deploying or mutating production without existing operator authorization |

## Self-check

- [ ] Task (`prepare` / `plan` / `execute` / `log-analysis` / `ops-diagnose`) and target (`release_ready` / `deployed` / read-only diagnosis) explicitly stated, with zero fabricated runs?
- [ ] For `log-analysis` / `ops-diagnose`: strictly read-only, `log_profiler.py` / evidence paths cited, secrets redacted, and zero unauthorized production mutations executed?
- [ ] Pre-deploy fingerprints match candidate SHA (`e2e` never null on UI), and **Deploy ≠ Release** enforced via dark Feature Flags + runtime `kill switch`?
- [ ] All **6 executable Runbook fields** present AND **actual staging rollback execution proof** recorded (measured timing + rollback-failure fallback; unexecuted prose = blocked) alongside graceful brownout verification?
- [ ] Money/ledger changes forbid destructive `downgrade` and specify compensation-only recovery; client binaries verify kill-switches, forced-upgrade floor and N-2 server APIs?
- [ ] **24-hour observation window + statistical quadruple SLO breakers** (`> baseline + 3σ` for `2m`, P95 `> 150%` SLO for `3m`, burn `> 5×` mean, business metric drop → auto-halt, freeze, one-click rollback, alert & forensics) wired with zero hardcoded ports/secrets?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [observability-and-incident.md](references/observability-and-incident.md) | SLI/SLO & error-budget governance, P0–P2 alerts, runbooks, four-phase incident response & escape attribution |
| [release-and-rollback.md](references/release-and-rollback.md) | Runtime readiness, shared-worktree safety, rehearsed rollback, graceful brownout, ledger compensation & client binary SOP |
| [industry-delivery-sops.md](../impl-evidence/references/industry-delivery-sops.md) | Archetype-specific operational invariants (fintech compensation, game tick/rollback, IoT/mobile binary floors, AI cost circuit breakers) |
| [templates/readiness.md](templates/readiness.md) | Pre-QC operational readiness evidence (`06-deliver/readiness.md`) |
| [templates/release-checklist.md](templates/release-checklist.md) | Deployment plan or executed release record (`06-deliver/checklist.md`) |
| [templates/incident-report.md](templates/incident-report.md) | Blameless incident postmortem & escape attribution |

> Defaults pattern from: `anthropics/skills@41bbe19` (claude-api SKILL.md 'Defaults' section, 2026-09-03) · verified incidents from a user project's history (toolchain drift, probe semantics, stuck processes)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
