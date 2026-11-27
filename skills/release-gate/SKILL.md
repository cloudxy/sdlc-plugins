---
name: "release-gate"
description: "Use this skill when the spawn packet names qc or $release-gate. Do NOT load in /sdlc or for writing tests."
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

Judge the authorized affected checks for the named candidate; a large unrelated suite is not stronger feature evidence. An older baseline failure is neither this change's regression nor an automatic waiver. Require the scope decision, any unresolved obligation and the final candidate's actual outputs; never promote a DOM/mock check, author self-check or selected cases into full-suite, independent or production acceptance.

| Target | What the opinion may say | Extra evidence before the opinion |
|---|---|---|
| `local_verified` | The build at `<version>` passes its applicable gates and acceptance locally | None beyond the six points |
| `release_ready` | `<version>` is ready for `<environment>` | SRE `deliver/prepare` evidence (`06-deliver/readiness.md`): artifact and config identity, deployment/config/migration compatibility, recovery feasibility, monitoring and operator ownership. Missing required operational evidence **blocks release readiness**, even when functional tests pass |

Deployment (`deliver/checklist`) runs after the opinion and only within existing user/release authority; the actual deployment is recorded separately by SRE. Unknown or untested is not pass; omitting an applicable gate needs a recorded scope decision.

## Product QC vs Process QA (Dual Audit Mandate)

Release gating separates **candidate inspection** from **systemic seam hygiene** — never conflate them and never skip either when in scope:
- **Product QC (`qc` — 本次候选产物质量控制)**: inspects *this candidate's* artifacts, 6-point FR/NFR/journey completeness, contract & test-submission entry gates (`test-report.md` §0), Feature-Flag dark-deploy & **actual staging rollback execution proof** (`只在文档写未在 staging 实测执行 = 无回滚路径 = 阻塞放行`), and `[SEC-n]` + non-bypassable PR `SAST` / Staging `DAST` closure.
- **Process QA (过程质量保证 — 系统性接缝防逃逸审计)**: audits systemic seam escapes across defect repairs (`bug-report.md` §7 & `state.yaml` `escape:`) and cycle reviews via **`escape.seam_fix` + `verified_by`**, verifying that whenever a defect leaked across an upstream seam, a concrete gate/assertion was added at that seam and independently verified so the recurring defect class is eliminated at its source. An escaped defect fix missing `escape.seam_fix` or `verified_by` blocks `放行`.

## Six-point completeness check

1. **FR list ↔ coverage matrix**: every FR/NFR/`EV-n`/`[SEC-n]` has at least one row? (The orchestrator runs `skills/coverage-matrix/scripts/check-matrix.py` and pastes the output — you do not execute scripts.)
2. **FR list ↔ design artifacts**: FRs with UI have `edge-states.md` and zero-`TBD` copy? (Missing `edge-states.md` = design stage was skipped entirely)
3. **FR list ↔ tickets & submission entry gate**: every FR has an implementing ticket, and `test-report.md` §0 (`提测准入核对`: contract tests, affected unit tests, exception GWT/AC traceability, deployable artifact) passed?
4. **Findings, security gates & Process-QA seam closure**: blocker/major all fixed, `[SEC-n]` + PR `SAST` + Staging `DAST` (where web/API exists) closed, and any escaped defect repair carries verified **`escape.seam_fix` + `verified_by`**?
5. **Gate fingerprints**: test/contract-test/sast/lint/build/migration/**e2e** (+ staging `dast` when applicable) all have commands + exit codes + timestamps run on the exact candidate SHA? For a UI change, `e2e` must be a pass, never null.
6. **Journeys, acceptance & staging rollback proof**: every `J-n` has an E2E row that ran at its consumer boundary; `04-verify/accept-pm.md`, `accept-design.md` (UI) and `accept-growth.md` (unless growth skipped) exist with verdicts (no `不通过`; `有条件通过` accepted with owners); for `release_ready`, `06-deliver/readiness.md` proves Feature-Flag `kill switch`, 6-field Runbook, 24h statistical SLO breakers, and **actual staging rollback execution** (unexecuted prose = block).

## Release decision (three tiers, for the declared target)

| Tier | Verdict line (`RELEASEOPINION` gate) | Condition |
|---|---|---|
| ✅ **Ship** | `结论：放行` | blocker=0, major=0, minor all resolved or waived, all applicable gates green with evidence, every acceptance verdict `通过`, and (for `release_ready`) `06-deliver/readiness.md` present |
| ⚠️ **Conditional** | `结论：有条件放行` | minor unresolved but waived with documented reason + owner, or acceptance `有条件通过` with human-accepted conditions |
| ❌ **Block** | `结论：不放行` | blocker > 0 OR major > 0 (without verified fix or explicit authorized human risk-owner escalation) OR any gate failed without documented human waiver OR any acceptance `不通过` OR a J-n without an E2E run OR (for `release_ready`) required readiness evidence missing |

Emit the exact single-choice verdict line (`结论：放行`, `结论：有条件放行`, or `结论：不放行` — never leave multiple options on the `结论：` line) so the `RELEASEOPINION` gate can parse it deterministically. Gate failures and blocker/major findings are never waived by `qc` — they are fixed with fresh gate fingerprints or escalated to an authorized human risk owner for explicit waiver. A waiver names the affected criterion, version and environment, the risk owner, the reason, a compensating control and an expiry or recheck condition. Never accept a waiver of legal, security or organizational prohibitions from someone without the authority to override them.

## Handoff contract

| Direction | Content |
|---|---|
| **Input needed** | `qa` `04-verify/coverage.md` + test-report · `reviewer` findings + status · gate outputs (cmd + exit code) · spec FR/NFR · constitution · the packet's target, version and environment · for `release_ready`: SRE `06-deliver/readiness.md` |
| **Output** | Release opinion in your **final message** (ship / conditional / block for the named target) — do not Write files; the orchestrator saves [templates/release-opinion.md](templates/release-opinion.md) |
| **Refuse** | Fixing code · re-reviewing (→ reviewer already did) · changing gate verdicts · writing test cases · authorizing or claiming deployment and announcements |

## Self-check

- [ ] Target (`local_verified` | `release_ready`), version and environment named in the opinion?
- [ ] **Product QC** (candidate artifacts, contract/submission gates, `[SEC-n]`/SAST/DAST, actual staging rollback proof) AND **Process QA** (`escape.seam_fix` + `verified_by` on escaped defect repairs) both audited?
- [ ] Six-point completeness check walked through (incl. journeys and acceptance verdicts)?
- [ ] Every finding has a status (fixed/waived with reason)?
- [ ] Gate fingerprints present (command + exit code + timestamp) for the version under decision?
- [ ] `release_ready`: SRE readiness evidence (incl. executed staging rollback proof, not prose-only) consumed, or its absence recorded as a block?
- [ ] Release decision is explicit (not "looks good") and does not claim deployment or announcement?
- [ ] Waivers have: criterion + reason + owner + compensating control + re-evaluation condition?

## Templates

| File | Use when |
|---|---|
| [templates/release-opinion.md](templates/release-opinion.md) | Shape of the ship / conditional / block opinion |

> Boundary discipline pattern from: `anthropics/skills@41bbe19` (discernment-nudge SKILL.md 'When not to' section, 2026-09-03)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
