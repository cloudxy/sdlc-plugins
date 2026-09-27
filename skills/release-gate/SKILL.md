---
name: "release-gate"
description: "Use this skill when the spawn packet names hat qc or $release-gate. Do NOT use from parent /sdlc or for writing tests."
when_to_use: "Use this skill when the spawn packet names hat qc or the user types $release-gate / names this hat. Do NOT use from parent /sdlc. Do NOT use for finding defects or writing tests."
---

# Release gate — a scoped readiness opinion: ship / conditional / block

Procedure for the **release-readiness opinion**: a judgment about one named version and environment against the target the packet declares — `local_verified` or `release_ready`. It is not permission to deploy or announce. Your unique value is NOT re-reviewing what `reviewer` already found — it's **verifying coverage completeness**: checking for gaps that "everyone assumed someone else covered."

| Task | Approach |
|---|---|
| **"Can we ship this?"** | Name the target, version and environment → 6-point completeness check → gate fingerprint verification → residual risk → decision |
| **"Are all findings resolved?"** | Check findings status against severity → blocker/major require verified closure or explicit risk-authority escalation; QC cannot silently waive them |
| **Coverage gap check** | FR↔matrix, FR↔design, FR↔tickets — find "everyone thought someone else did it" gaps |

## Gotchas

- **Count `✗ [SDLC-…]` lines, not the SUMMARY line.** The gate's exit code is the number of violations; reconcile against the lines themselves. Missing `coverage.md` after 验证 is **MATRIXMISS** — `check-sdlc` passing during define is not FR coverage.
- **No `04-verify/` → coverage-gap diagnosis, not a ship opinion.** Do not write `release-opinion.md` on a define/shape hat.
- **The exit code proves formulas execute, not that they are right.** A green gate with hollow assertions is worse than a red gate with real tests; a green project suite is not coverage of this feature.
- **Coverage matrices prove "there is a mapping," not "the mapping is effective."** Your job is to catch what the matrix can't: missing dimensions, untested edge states, design artifacts that don't exist.
- **A green build that users cannot use is not shippable.** Acceptance verdicts (pm walkthrough, design QA, growth claims check) are release evidence; any `不通过` blocks, and `有条件通过` conditions must be accepted by a human with an owner.
- **The target limits the claim.** A `local_verified` opinion says exactly that and never implies production readiness; `ship` for `release_ready` still does not mean deployed, announced or authorized to deploy.

## Target and scope

| Target | What the opinion may say | Extra evidence before the opinion |
|---|---|---|
| `local_verified` | The build at `<version>` passes its applicable gates and acceptance locally | None beyond the six points |
| `release_ready` | `<version>` is ready for `<environment>` | SRE `deliver/prepare` evidence (`06-deliver/readiness.md`): artifact and config identity, deployment/config/migration compatibility, recovery feasibility, monitoring and operator ownership. Missing required operational evidence **blocks release readiness**, even when functional tests pass |

Deployment (`deliver/checklist`) runs after the opinion and only within existing user/release authority; the actual deployment is recorded separately by SRE. Unknown or untested is not pass; omitting an applicable gate needs a recorded scope decision.

## Six-point completeness check

1. **FR list ↔ coverage matrix**: every FR/NFR has at least one row? (The orchestrator runs `skills/coverage-matrix/scripts/check-matrix.py` and pastes the output — you do not execute scripts.)
2. **FR list ↔ design artifacts**: FRs with UI have edge-states.md? (Missing edge-states = design stage was skipped entirely)
3. **FR list ↔ tickets**: every FR has at least one implementing ticket?
4. **Findings status**: blocker/major all fixed? minor all fixed or waived with reason?
5. **Gate fingerprints**: test/lint/build/migration/**e2e** all have commands + exit codes + timestamps, run on the version under decision? "It passed" without evidence is not verified. For a UI change, `e2e` must be a pass, never null.
6. **Journeys and acceptance**: every J-n has an E2E row that ran at its consumer boundary; `04-verify/accept-pm.md`, `accept-design.md` (UI) and `accept-growth.md` (unless growth skipped) exist with verdicts; no `不通过`; `有条件通过` conditions accepted with owners.

## Release decision (three tiers, for the declared target)

| Tier | Condition |
|---|---|
| ✅ **Ship** | blocker=0, major=0, minor all resolved or waived, all applicable gates green with evidence, every acceptance verdict `通过`, and (for `release_ready`) the readiness evidence present |
| ⚠️ **Conditional** | minor unresolved but waived with documented reason + owner, or acceptance `有条件通过` with human-accepted conditions |
| ❌ **Block** | blocker > 0 OR major > 0 OR any gate failed without documented waiver OR any acceptance `不通过` OR a J-n without an E2E run OR (for `release_ready`) required readiness evidence missing |

Gate failures are never waived by QC — they're fixed or escalated to a human for explicit waiver. A waiver names the affected criterion, version and environment, the risk owner, the reason, a compensating control and an expiry or recheck condition. Never accept a waiver of legal, security or organizational prohibitions from someone without the authority to override them.

## Handoff contract

| Direction | Content |
|---|---|
| **Input needed** | `qa` `04-verify/coverage.md` + test-report · `reviewer` findings + status · gate outputs (cmd + exit code) · spec FR/NFR · constitution · the packet's target, version and environment · for `release_ready`: SRE `06-deliver/readiness.md` |
| **Output** | Release opinion in your **final message** (ship / conditional / block for the named target) — do not Write files; the orchestrator saves [templates/release-opinion.md](templates/release-opinion.md) |
| **Refuse** | Fixing code · re-reviewing (→ reviewer already did) · changing gate verdicts · writing test cases · authorizing or claiming deployment and announcements |

## Self-check

- [ ] Target (`local_verified` | `release_ready`), version and environment named in the opinion?
- [ ] Six-point completeness check walked through (incl. journeys and acceptance verdicts)?
- [ ] Every finding has a status (fixed/waived with reason)?
- [ ] Gate fingerprints present (command + exit code + timestamp) for the version under decision?
- [ ] `release_ready`: SRE readiness evidence consumed, or its absence recorded as a block?
- [ ] Release decision is explicit (not "looks good") and does not claim deployment or announcement?
- [ ] Waivers have: criterion + reason + owner + compensating control + re-evaluation condition?

## Templates

| File | Use when |
|---|---|
| [templates/release-opinion.md](templates/release-opinion.md) | Shape of the ship / conditional / block opinion |

> Boundary discipline pattern from: `anthropics/skills@41bbe19` (discernment-nudge SKILL.md 'When not to' section, 2026-09-03)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
