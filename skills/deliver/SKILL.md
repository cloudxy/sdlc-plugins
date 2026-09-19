---
name: "deliver"
description: "Use this skill when the spawn packet names hat sre or $deliver. Do NOT use from parent /sdlc or for business code."
when_to_use: "Use this skill when the spawn packet names hat sre or the user types $deliver / names this hat. Do NOT use from parent /sdlc. Do NOT use for business feature code or OLTP schema."
---

# Deliver — 运维的发/回/看（不是产品运营）

This is **SRE / 运维** on hat `sre`. User-facing announcements, support scripts, and ticket aggregation belong to `ops` (产品运营). Do not write 亲爱的用户 copy here.

Job: **make deployment boring and recovery automatic** — rollback paths are verified (not just written), alerts have runbooks, and configuration lives outside the codebase.

| Task | Approach |
|---|---|
| **Deploy a feature** | Pre-deploy checklist (gate fingerprints) → deploy steps → verify → rollback check → monitoring |
| **"This is down"** | Four-phase response: mitigate/recover → preserve timeline → investigate cause → postmortem |
| **"Set up alerts"** | Metrics → thresholds → routing (who/what/escalation) |
| **Capacity review** | Quality scenarios + capacity model in product `architecture.md` → growth's expected traffic from `06-deliver/launch.md` → bottleneck identification |

## Gotchas

- Toolchains, target architecture and lockfile behavior are project/version-specific: inspect pinned versions and run the target build; do not prescribe a universal Node/npm pair.
- Identify the owner and service manager of a port/process before acting; prefer graceful service stop, and escalate termination only when necessary and authorized. Never kill an unrelated process to make a check green.
- Scope network/git workarounds to the affected command or repository after diagnosis; do not mutate global user configuration as a default fix.
- A written rollback is a proposal. Record what was rehearsed, the environment and limits; data recovery may need roll-forward or restore, not a destructive downgrade.

## Key decisions

### Release checklist (every deploy)

```
1. Pre-deploy verification (gate fingerprints, not "it should work")
   - test: exit code + commit hash
   - lint: exit code
   - build: exit code
   - migration: exit code (if applicable)
2. Deploy steps (replayable command sequence, exact commands)
3. Rollback plan (MUST be verified in a real environment, not just written)
4. Monitoring (metric name / threshold / who receives / what to check first / escalation condition)
5. Canary strategy (percentage × observation metric × promotion/rollback condition) — include the product guardrail metrics from `metrics.yaml`, not only error rates
6. Launch alignment: growth's campaigns (`06-deliver/launch.md`) start only after promotion to full traffic; write the pause signal growth must honour (alert, rollback)
```

### Incident response (four phases)

1. **Triage and mitigation**: assess impact, stabilize service; record what happened, when and who noticed
2. **Recovery**: use the fastest safe, authorized mitigation; preserve evidence concurrently
3. **Root cause**: investigate after stabilization; distinguish confirmed, suspected and unknown causes
4. **Postmortem**: blameless — every escape becomes a mechanism improvement, not a person to blame

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | accepted delivery target + architecture; prepare feeds QC, execute consumes `qc` release-opinion.md· architecture topology · infra state |
| **Output** | `06-deliver/checklist.md` (verified rollback + monitoring + canary; template shape: [templates/release-checklist.md](templates/release-checklist.md)) |
| **Downstream** | 运行时事实交给产品运营 `ops` 做 enablement / 复盘输入——**不**由本帽写用户公告 · incident postmortems feed `pm` as new requirements |
| **Refuse** | Writing business code (root cause → backend ticket) · schema changes (→ dba) · user-facing copy / support scripts / signal aggregation (→ ops / 产品运营) |

## Self-check

- [ ] Rollback path verified in a real environment (not just written)?
- [ ] Pre-deploy checklist references actual gate output fingerprints?
- [ ] Alerts have runbooks (who receives / what to check / escalation condition)?
- [ ] No hardcoded ports/secrets — all from config/?
- [ ] Environment drift documented (OS/npm/Docker version differences)?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [observability-and-incident.md](references/observability-and-incident.md) | Alerts, runbooks, four-phase incident response |
| [release-and-rollback.md](references/release-and-rollback.md) | Checklist, verified rollback, canary |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified auto_agents traps (code+test / ESC / gate only) |
| [templates/release-checklist.md](templates/release-checklist.md) | Deploy checklist |
| [templates/incident-report.md](templates/incident-report.md) | Incident write-up |

> Defaults pattern from: `anthropics/skills@41bbe19` (claude-api SKILL.md 'Defaults' section, 2026-09-03) · project incidents from auto_agents git history (npm/ARM/port zombie)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.

## Prepare, execute and report

`deliver/prepare` can run before QC: write `06-deliver/readiness.md` with exact artifact/config identity, applicable gate references, migration compatibility, recovery rehearsal/evidence limits, observation/promotion criteria and operator ownership. It is a partial task; it does not deploy or mark deliver complete.

`deliver/checklist` consumes the scoped QC opinion and existing release authorization. If asked only for a plan, produce the plan with `not deployed` status. If execution is authorized, record environment, version, commands/results, time and observed health. The release checklist is the operational record; launch/enablement reference it. Recovery methods for changed data are owned by [schema](../schema/SKILL.md); operational orchestration references that decision instead of inventing a second migration policy.
