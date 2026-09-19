---
name: "release-gate"
description: "Use this skill when the spawn packet names hat qc or $release-gate. Do NOT use from parent /sdlc or for writing tests."
when_to_use: "Use this skill when the spawn packet names hat qc or the user types $release-gate / names this hat. Do NOT use from parent /sdlc. Do NOT use for finding defects or writing tests."
---

# Release gate — ship / conditional / block

Procedure for the **final release decision**. Your unique value is NOT re-reviewing what `reviewer` already found — it's **verifying coverage completeness**: checking for gaps that "everyone assumed someone else covered."

| Task | Approach |
|---|---|
| **"Can we ship this?"** | 6-point completeness check → gate fingerprint verification → residual risk → decision |
| **"Are all findings resolved?"** | Check findings status against severity → blocker/major require verified closure or explicit risk-authority escalation; QC cannot silently waive them |
| **Coverage gap check** | FR↔matrix, FR↔design, FR↔tickets — find "everyone thought someone else did it" gaps |

## Gotchas

- **Count `✗ [SDLC-…]` lines, not the SUMMARY line.** Plugin 3.6.0 stopped incrementing V on SUMMARY; older copies still did (exit N+1). Missing `coverage.md` after 验证 is **MATRIXMISS** — `check-sdlc` pass during define is not FR coverage.
- **No `04-verify/` → coverage-gap diagnosis, not a ship opinion.** Do not write `release-opinion.md` on a define/shape hat.
- **The exit code proves formulas execute, not that they are right.** A green gate with hollow assertions is worse than a red gate with real tests.
- **Coverage matrices prove "there is a mapping," not "the mapping is effective."** Your job is to catch what the matrix can't: missing dimensions, untested edge states, design artifacts that don't exist.
- **A green build that users cannot use is not shippable.** Acceptance verdicts (pm walkthrough, design QA, growth claims check) are release evidence; any `不通过` blocks, and `有条件通过` conditions must be accepted by a human with an owner.

## Six-point completeness check

1. **FR list ↔ coverage matrix**: every FR/NFR has at least one row? (The orchestrator runs `skills/coverage-matrix/scripts/check-matrix.py` and pastes the output — you do not execute scripts.)
2. **FR list ↔ design artifacts**: FRs with UI have edge-states.md? (Missing edge-states = design stage was skipped entirely)
3. **FR list ↔ tickets**: every FR has at least one implementing ticket?
4. **Findings status**: blocker/major all fixed? minor all fixed or waived with reason?
5. **Gate fingerprints**: test/lint/build/migration/**e2e** all have commands + exit codes + timestamps? "It passed" without evidence is not verified. For a UI change, `e2e` must be a pass, never null.
6. **Journeys and acceptance**: every J-n has an E2E row that ran; `04-verify/accept-pm.md`, `accept-design.md` (UI) and `accept-growth.md` (unless growth skipped) exist with verdicts; no `不通过`; `有条件通过` conditions accepted with owners.

## Release decision (three tiers)

| Tier | Condition |
|---|---|
| ✅ **Ship** | blocker=0, major=0, minor all resolved or waived, all gates green with evidence, every acceptance verdict `通过` |
| ⚠️ **Conditional** | minor unresolved but waived with documented reason + owner, or acceptance `有条件通过` with human-accepted conditions |
| ❌ **Block** | blocker > 0 OR major > 0 OR any gate failed without documented waiver OR any acceptance `不通过` OR a J-n without an E2E run |

Gate failures are never waived by QC — they're fixed or escalated to human for explicit waiver with reason and owner.

## Handoff contract

| Direction | Content |
|---|---|
| **Input needed** | `qa` `04-verify/coverage.md` + test-report · `reviewer` findings + status · gate outputs (cmd + exit code) · spec FR/NFR · constitution. SRE `06-deliver/readiness.md` when the target is release-ready; deployment execution follows QC and the existing release authorization. |
| **Output** | Release opinion in your **final message** (ship / conditional / block) — do not Write files; the orchestrator saves [templates/release-opinion.md](templates/release-opinion.md) |
| **Refuse** | Fixing code · re-reviewing (→ reviewer already did) · changing gate verdicts · writing test cases |

## Self-check

- [ ] Six-point completeness check walked through (incl. journeys and acceptance verdicts)?
- [ ] Every finding has a status (fixed/waived with reason)?
- [ ] Gate fingerprints present (command + exit code + timestamp)?
- [ ] Release decision is explicit (not "looks good")?
- [ ] Waivers have: reason + owner + re-evaluation condition?

## Templates

| File | Use when |
|---|---|
| [templates/release-opinion.md](templates/release-opinion.md) | Shape of the ship / conditional / block opinion |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified gate traps (SUMMARY, skip=pass, hollow tests) |

> Boundary discipline pattern from: `anthropics/skills@41bbe19` (discernment-nudge SKILL.md 'When not to' section, 2026-09-03)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.

## Decision scope

The packet declares the target: local verification or release readiness. A local verification opinion must say “local_verified”, not imply production readiness. For release readiness consume SRE `deliver/prepare` evidence before the opinion: artifact identity, deployment/config/migration compatibility, recovery feasibility, monitoring and ownership. Missing required operational evidence blocks **release readiness**, even when functional tests pass.

“Ship” is a readiness opinion for a named version/environment, not permission to deploy or announce. `deliver/checklist` executes only within existing user/release authority; record actual deployment separately. A waiver must name the affected criterion/version/environment, risk owner, reason, compensating control and expiry/recheck condition. Never waive legal, security or organizational prohibitions the approver has no authority to override. Unknown/untested is not pass; applicable-gate omissions require a recorded scope decision.
