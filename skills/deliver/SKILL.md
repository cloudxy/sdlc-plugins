---
name: "deliver"
description: "Use this skill when the spawn packet names hat sre or $deliver. Do NOT use from parent /sdlc or for business code."
when_to_use: "Use this skill when the spawn packet names hat sre or the user types $deliver / names this hat. Do NOT use from parent /sdlc. Do NOT use for business feature code or OLTP schema."
---

# Deliver — 运维的发/回/看（不是产品运营）

This is **SRE / 运维** on hat `sre`. User-facing announcements, support scripts, and ticket aggregation belong to `ops` (产品运营). Do not write 亲爱的用户 copy here.

Job: **make deployment boring and recovery automatic** — rollback paths are verified (not just written), alerts have runbooks, and configuration lives outside the codebase.

| Task | When | Approach |
|---|---|---|
| **Prepare** (`deliver/prepare`) | Before QC, for `release_ready` / `deployed` targets | Write `06-deliver/readiness.md`: exact artifact and config identity, applicable gate references, migration compatibility, recovery rehearsal and its limits, observation and promotion criteria, operator ownership. A partial task: it deploys nothing and does not complete deliver |
| **Release checklist — plan** (`deliver/checklist`) | The user asked for a plan, or execution is not authorized | [templates/release-checklist.md](templates/release-checklist.md) with status `not deployed` |
| **Release checklist — execute** (`deliver/checklist`) | After the scoped QC opinion, within existing release authorization | Pre-deploy fingerprints → deploy steps → verify → rollback check → monitoring; record environment, version, commands and results, time, observed health. Recovery inside this authorized release (restart, rollback) follows the same checklist |
| **CI wiring** (`deliver/ci`) | Pipeline wiring changes | Primary skill `sdlc-workflow:cicd` |
| **"This is down"** | Solo `$deliver` only — independent incident command and on-call are outside the /sdlc slice and have no registered task | Four-phase response: mitigate/recover → preserve timeline → investigate cause → postmortem. Solo use grants no production permissions; every operating action needs the operator's authorization |
| **"Set up alerts"** | Checklist monitoring section, or solo | Metrics → thresholds → routing (who/what/escalation) |
| **Capacity review** | When launch traffic or scenarios change | Quality scenarios + capacity model in product `architecture.md` → growth's expected traffic from `06-deliver/launch.md` → bottleneck identification |

## Gotchas

- Toolchains, target architecture and lockfile behavior are project/version-specific: inspect pinned versions and run the target build on the CI platform/architecture; a green local build on another architecture proves nothing about it.
- Identify the owner and service manager of a port/process before acting; prefer graceful service stop, and escalate termination only when necessary and authorized. Never kill an unrelated process to make a check green.
- Scope network/git workarounds to the affected command or repository after diagnosis; do not mutate global user configuration as a default fix.
- A written rollback is a proposal. Record what was rehearsed, the environment and limits; data recovery may need roll-forward or restore, not a destructive downgrade.
- **Health probes that orchestrators act on must fail (non-2xx) when a required dependency fails.** A probe that always answers 200 keeps a hung service "alive"; keep human diagnostic endpoints separate from the probe the orchestrator reads.
- **Safety defaults are only safe once exercised on the real path.** A dry-run that skips the alerting or kill branch proves nothing about it; run one real failure round in a safe environment.
- **Runbooks and postmortems live in committed paths.** A runbook link into an ignored or uncommitted directory is a dead link for on-call and new clones.

## Key decisions

### Release checklist (every deploy)

```
1. Pre-deploy verification (gate fingerprints, not "it should work")
   - test: exit code + commit hash
   - lint: exit code
   - build: exit code
   - migration: exit code (if applicable)
2. Deploy steps (replayable command sequence, exact commands)
3. Rollback plan (verified in a real environment for release_ready/deployed targets; otherwise state what was rehearsed and what was not)
4. Monitoring (metric name / threshold / who receives / what to check first / escalation condition)
5. Canary strategy (percentage × observation metric × promotion/rollback condition) — include the product guardrail metrics from `metrics.yaml`, not only error rates
6. Launch alignment: growth's campaigns (`06-deliver/launch.md`) start only after promotion to full traffic; write the pause signal growth must honour (alert, rollback)
```

### Incident response (four phases)

1. **Triage and mitigation**: assess impact, stabilize service; record what happened, when and who noticed
2. **Recovery**: use the fastest safe, authorized mitigation; preserve evidence concurrently
3. **Root cause**: investigate after stabilization; distinguish confirmed, suspected and unknown causes
4. **Postmortem**: blameless — every escape becomes a mechanism improvement, not a person to blame. Record it in the project's `.sdlc/_lessons.md`; it can later be cited as a signal by ops

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | accepted delivery target + architecture; prepare feeds QC, execute consumes `qc` release-opinion.md · architecture topology · infra state |
| **Output** | `06-deliver/readiness.md` (prepare) · `06-deliver/checklist.md` (rollback + monitoring + canary; plan or executed record; template shape: [templates/release-checklist.md](templates/release-checklist.md)) · incident write-ups from solo use ([templates/incident-report.md](templates/incident-report.md)) |
| **Downstream** | 运行时事实交给产品运营 `ops` 做 enablement / 复盘输入——**不**由本帽写用户公告 · incident postmortems feed `pm` as requirement candidates through ops signals · enablement and launch reference the executed checklist for availability |
| **Refuse** | Writing business code (root cause → backend ticket) · schema changes (→ dba) · user-facing copy / support scripts / signal aggregation (→ ops / 产品运营) · deploying without existing authorization |

Recovery methods for changed data are owned by [schema](../schema/SKILL.md); operational orchestration references that decision instead of inventing a second migration policy.

## Self-check

- [ ] Task and target named (prepare / plan / execute; `release_ready` or `deployed`)?
- [ ] Prepare and plan: rehearsed vs unrehearsed recovery steps stated, with environment and limits?
- [ ] Execute (and any `release_ready` readiness): rollback path verified in a real environment, or its absence recorded as a blocker?
- [ ] Pre-deploy checklist references actual gate output fingerprints?
- [ ] Alerts have runbooks (who receives / what to check / escalation condition) in committed paths?
- [ ] No hardcoded ports/secrets — all from config?
- [ ] Environment drift documented (OS/toolchain/container version differences)?
- [ ] Nothing claims "deployed" without the executed record (environment, version, time, observed health)?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [observability-and-incident.md](references/observability-and-incident.md) | Alerts, runbooks, four-phase incident response |
| [release-and-rollback.md](references/release-and-rollback.md) | Checklist, verified rollback, canary |
| [templates/release-checklist.md](templates/release-checklist.md) | Deploy checklist |
| [templates/incident-report.md](templates/incident-report.md) | Incident write-up |

> Defaults pattern from: `anthropics/skills@41bbe19` (claude-api SKILL.md 'Defaults' section, 2026-09-03) · verified incidents from a user project's history (toolchain drift, probe semantics, stuck processes)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
