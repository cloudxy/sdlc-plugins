---
name: "coverage-matrix"
description: "Use when designing tests, journey E2E or coverage matrices. In sdlc-workflow:qa or $coverage-matrix. Do NOT use while /sdlc runs or for release decisions."
when_to_use: "Use this skill when designing cases, coverage matrices, or defect reports. Load inside sdlc-workflow:qa, or $coverage-matrix. Do NOT use while /sdlc is running in this window. Do NOT use for fixing defects or release decisions."
---

# Coverage — risk-based tests, journey E2E, matrices, defect reports

Job: **find what will hurt users before they do** — prove the key journeys work end-to-end on the running product, the events are right, and nothing important is silently untested. A matrix proves mapping; journeys, exploration and real environments prove the product works.

| Task | Approach |
|---|---|
| **Early test plan** (`define/test-plan`) | Before implementation, write `01-define/test-plan.md`: acceptance IDs, critical failure modes, the cheapest layer that can falsify each risk, data/fixtures, environment and pending decisions. No execution results, no finished matrix, no project source writes |
| **New feature testing** (`verify/risk-based-tests`) | Reuse the test plan → risk map → a consumer-boundary journey check for every J-n → cases from GWT at the cheapest layer → tracking validation for every EV-n (`tracking: yes`) → exploratory charters → trace matrix → regression plan |
| **"Is this well covered?"** | Check matrix holes → boundary review → edge-states comparison (UI) |
| **Defect found** | Write defect ticket → verify fix → add to regression set |
| **Pre-release** | Regression selected by change impact; a full suite only where the project's release policy requires it → coverage matrix final check |

## Gotchas

- **Green unit tests, unusable product.** Every key journey J-n needs a real consumer-boundary check: a browser for UI, API/CLI/SDK/batch execution for other surfaces. The matrix label **E2E** marks journey-level checks; it does not require every assertion to use a browser, and screenshots are evidence only for UI. `e2e: null` is not acceptable for a UI change (v4 gate `E2E`). Details: [e2e-and-exploratory.md](references/e2e-and-exploratory.md).
- **Scripted tests only find what you imagined.** Run at least one exploratory charter on the riskiest area per L2+ feature and log it.
- **Events are features.** With `tracking: yes`, each EV-n gets a validation row (fired once, right properties, right identity), or the launch cannot be measured. The `collect` companion owns the event-validation method.
- **The matrix proves "there is a mapping," not "the mapping is effective."** `assert True` (or `… or True`) can fill a cell. Hole detection is mechanical; hollow testing is not — that's G-fresh's job.
- **Preconditions must be real state.** A Given that reads data must commit or persist it inside the same test; a case that relies on another test's leftovers passes alone and fails in another order.
- **SQLite silently accepts PostgreSQL syntax (like `NULLS LAST`).** SQLite unit tests can be useful but do not establish production-dialect correctness for affected SQL behavior — a verified production escape came from exactly this.
- **Cases may go beyond the literal GWT.** Derive boundary, concurrency, security and compatibility cases from accepted invariants; escalate an ambiguous business outcome to PM instead of guessing it, and do not stop only because a case was not spelled out.
- **Regression follows change impact** (story dependency graph). Full regression is a release-policy decision, not a per-ticket rule.

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

**Matrix holes are the verify exit condition** — every hole needs a test or a documented exemption with reasoning. Write the matrix to `04-verify/coverage.md` (gate path; not `trace-matrix.md` as the filename). `check-matrix.py` requires every FR / NFR / EV-n id in the matrix and every J-n on a row marked **E2E**. Test code and run results stay canonical; the matrix indexes them by ID and version instead of copying assertions.

### Environment fidelity

Test environment must match the production properties relevant to the risk; record residual differences. SQL dialect differences (SQLite vs MySQL vs PostgreSQL) are the most common silent escape. For any SQL feature that varies by dialect, either use the real DB or mark as "needs real-DB verification."

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | spec (FR/NFR, journeys J-n) · `01-define/test-plan.md` · `01-define/tracking.md` (EV-n) · implementation evidence + integration files · edge-states matrix (UI) · API contracts · running app (`app.base_url`) |
| **Output** | define: `01-define/test-plan.md` · verify: `04-verify/coverage.md` (matrix shape: [templates/trace-matrix.md](templates/trace-matrix.md)) · E2E run (recorded as script gate `e2e`) · `test-report.md` incl. exploratory sessions · defect tickets |
| **Source writes** | verify tasks may write assigned test code, fixtures and test-runner configuration through the packet's `source_writes`; inspection-only runs omit it; `define/test-plan` never writes project source. None of this authorizes product-code fixes or a changed business oracle |
| **Downstream** | Defect tickets → implement rework · `04-verify/coverage.md` → `qc` |
| **Refuse** | Fixing defects (write tickets, don't fix) · release decisions (→ qc) · writing implementation code |

## Self-check

- [ ] define/test-plan: acceptance IDs, failure modes, layers, fixtures, environment and pending decisions — and no invented execution results?
- [ ] verify: every journey J-n has an E2E row that actually ran at its consumer boundary (browser with failure screenshots for UI; real API/CLI/SDK/batch calls otherwise)?
- [ ] `tracking: yes`: every EV-n has a validation row?
- [ ] L2+ verify: at least one exploratory charter run and logged?
- [ ] Every FR/NFR has at least one row in the matrix (or a documented exemption)?
- [ ] Boundary cases tested where the risk applies (empty/oversized/concurrent/unauthorized)?
- [ ] UI: edge-states from design compared screen by screen?
- [ ] Assertions are related to the standard (not assert True)?
- [ ] Defect reports have repro steps + expected vs actual + evidence?
- [ ] Fixed defects added to regression set?
- [ ] Test environment matches the production properties each risk depends on (SQL dialect when SQL behavior changed); residual differences recorded?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [e2e-and-exploratory.md](references/e2e-and-exploratory.md) | Journey E2E scope and discipline, tracking validation rows, exploratory charters and heuristics |
| [case-derivation.md](references/case-derivation.md) | Deriving cases from GWT (happy / empty / unauthorized / transitions) |
| [test-layering.md](references/test-layering.md) | Unit / integration / E2E split, dialect fidelity |
| [templates/trace-matrix.md](templates/trace-matrix.md) | FR ↔ case matrix |
| [templates/test-report.md](templates/test-report.md) | Test report |
| [templates/bug-report.md](templates/bug-report.md) | Defect ticket |
| `scripts/check-matrix.py` | Mechanical hole detection. G-script `--hat verify` / any run with `coverage.md` on disk invokes this (FR **and** NFR). |

> Gotchas based on: `anthropics/skills@41bbe19` (webapp-testing Common Pitfall pattern, 2026-09-03) · a verified production dialect escape (ESC-2)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
