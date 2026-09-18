---
name: "coverage-matrix"
description: "Use when designing tests, journey E2E or coverage matrices. In sdlc-workflow:qa or $coverage-matrix. Do NOT use while /sdlc runs or for release decisions."
when_to_use: "Use this skill when designing cases, coverage matrices, or defect reports. Load inside sdlc-workflow:qa, or $coverage-matrix. Do NOT use while /sdlc is running in this window. Do NOT use for fixing defects or release decisions."
---

# Coverage — risk-based tests, journey E2E, matrices, defect reports

Job: **find what will hurt users before they do** — prove the key journeys work end-to-end on the running product, the events are right, and nothing important is silently untested. A matrix proves mapping; journeys, exploration and real environments prove the product works.

| Task | Approach |
|---|---|
| **New feature testing** | Risk map → journey E2E for every J-n → cases from GWT at the cheapest layer → tracking validation for every EV-n → exploratory charters → trace matrix → regression plan |
| **"Is this well covered?"** | Check matrix holes → boundary review → edge-states comparison |
| **Defect found** | Write defect ticket → verify fix → add to regression set |
| **Pre-release** | Full regression on affected modules → coverage matrix final check |

## Gotchas

- **Green unit tests, unusable product.** Every key journey J-n needs an E2E run on the running app from a real starting point (new account, empty data) to the Aha moment. `e2e: null` is not acceptable for a UI change (v4 gate `E2E`). Details: [e2e-and-exploratory.md](references/e2e-and-exploratory.md).
- **Scripted tests only find what you imagined.** Run at least one exploratory charter on the riskiest area per L2+ feature and log it.
- **Events are features.** Each EV-n gets a validation row (fired once, right properties, right identity), or the launch cannot be measured.
- **The matrix proves "there is a mapping," not "the mapping is effective."** `assert True` can fill a cell. Hole detection is mechanical; hollow testing is not — that's G-fresh's job.
- **SQLite silently accepts PostgreSQL syntax (like `NULLS LAST`).** SQL dialect features need real-DB verification — this caused a production incident.
- **Test environment must match production dialect.** If tests pass on SQLite but production runs MySQL, you haven't tested.
- **Regression only runs affected surface** (from story dependency graph) — full regression is for pre-release, not every ticket.

## Key decisions

### Deriving test cases from GWT

For each FR's acceptance criteria:
1. **Happy path**: the Given/When/Then as written
2. **Empty/boundary**: what if the input is empty, at the limit, or just over the limit?
3. **Unauthorized**: what if the user lacks permission?
4. **State transitions**: legal and illegal flows from the PRD

### Trace matrix format

| FR/NFR | Test Case | File:Line | Result | Notes |
|---|---|---|---|---|
| FR-01 | TC-001 | test_file.py:12 | ✅ | |
| FR-03 | — | — | ❌ hole | Must add test or document exemption |

**Matrix holes are the verify exit condition** — every hole needs a test or a documented exemption with reasoning. Write the matrix to `04-verify/coverage.md` (gate path; not `trace-matrix.md` as the filename). `check-matrix.py` requires every FR / NFR / EV-n id in the matrix and every J-n on a row marked **E2E**.

### Environment fidelity

Test environment must match production. SQL dialect differences (SQLite vs MySQL vs PostgreSQL) are the most common silent escape. For any SQL feature that varies by dialect, either use the real DB or mark as "needs real-DB verification."

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | spec (FR/NFR, journeys J-n) · `01-define/tracking.md` (EV-n) · implementation evidence + integration files · edge-states matrix · API contracts · running app (`app.base_url`) |
| **Output** | `04-verify/coverage.md` (matrix shape: [templates/trace-matrix.md](templates/trace-matrix.md)) · E2E run (recorded as script gate `e2e`) · `test-report.md` incl. exploratory sessions · defect tickets |
| **Downstream** | Defect tickets → implement rework · `04-verify/coverage.md` → `qc` |
| **Refuse** | Fixing defects (write tickets, don't fix) · release decisions (→ qc) · writing implementation code |

## Self-check

- [ ] Every journey J-n has an E2E row that ran on the running app, with failure screenshots configured?
- [ ] Every EV-n has a validation row?
- [ ] At least one exploratory charter run and logged (L2+)?
- [ ] Every FR/NFR has at least one row in the matrix?
- [ ] Boundary cases tested (empty/oversized/concurrent/unauthorized)?
- [ ] Edge-states from design compared screen by screen?
- [ ] Assertions are related to the standard (not assert True)?
- [ ] Defect reports have repro steps + expected vs actual + evidence?
- [ ] Fixed defects added to regression set?
- [ ] Test environment matches production dialect?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [e2e-and-exploratory.md](references/e2e-and-exploratory.md) | Journey E2E scope and discipline, tracking validation rows, exploratory charters and heuristics |
| [case-derivation.md](references/case-derivation.md) | Deriving cases from GWT (happy / empty / unauthorized / transitions) |
| [test-layering.md](references/test-layering.md) | Unit / integration / E2E split, dialect fidelity |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified auto_agents traps (code+test / ESC / gate only) |
| [templates/trace-matrix.md](templates/trace-matrix.md) | FR ↔ case matrix |
| [templates/test-report.md](templates/test-report.md) | Test report |
| [templates/bug-report.md](templates/bug-report.md) | Defect ticket |
| `scripts/check-matrix.py` | Mechanical hole detection. G-script `--hat verify` / any run with `coverage.md` on disk invokes this (FR **and** NFR). |

> Gotchas based on: `anthropics/skills@41bbe19` (webapp-testing Common Pitfall pattern, 2026-09-03) · ESC-2 from auto_agents production incident

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
