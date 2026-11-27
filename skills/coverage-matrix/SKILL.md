---
name: "coverage-matrix"
description: "Use when designing tests, journey E2E or coverage matrices. In sdlc-workflow:qa or $coverage-matrix. Do NOT load in /sdlc or for release decisions."
when_to_use: "Use this skill when designing cases, coverage matrices, or defect reports. Load inside sdlc-workflow:qa, or $coverage-matrix. Do NOT use while /sdlc is running in this window. Do NOT use for fixing defects or release decisions."
---

# Coverage — risk-based tests, journey E2E, matrices, defect reports

Job: **find what will hurt users before they do** — prove the key journeys work end-to-end on the running product, the invariants hold beyond hand-picked examples, the events and security controls are anchored, and nothing important is silently untested.

| Task | Approach |
|---|---|
| **Early test plan** (`define/test-plan`) | Before implementation, write `01-define/test-plan.md` ([templates/test-plan.md](templates/test-plan.md)): audit AC testability/ambiguity/exception completeness, list acceptance IDs (`FR`/`NFR`/`J-n`/`EV-n`/`SEC-n`), critical failure modes, cheapest falsifying layer, conservation/metamorphic oracles & AI golden-eval gates, fixtures/dialect fidelity and pending decisions. No execution results, no finished matrix, no project source writes |
| **New feature testing** (`verify/risk-based-tests`) | Check **Test-Submission Entry Checklist (提测准入清单, §0 of `test-report.md` — bounce straight back to `implement` on any missing item)** → reuse `test-plan.md` → consumer-boundary journey check for every `J-n` → GWT + invariant cases at the cheapest layer → `[SEC-n]` control verification → tracking validation for every `EV-n` (`tracking: yes`) → exploratory charters → `04-verify/coverage.md` → targeted regression |
| **"Is this well covered?"** | Check matrix holes (`File:Line` anchored) → oracle strength (non-hollow, conservation/metamorphic) → boundary & edge-states review |
| **Defect found** | Follow the 5-stage lifecycle (`提交 → 确认 → 修复 → 验证 → 关闭`), grade severity strictly by **observable user & business impact** (never opinion), bind reproduction + expected baseline, and fill **Process-QA Seam Escape (`## 7` in [templates/bug-report.md](templates/bug-report.md))** on escaped bugs → independent fix verification → impact-based targeted regression |
| **Pre-release** | Targeted regression strictly scoped to affected modules/journeys (full-suite runs are prohibited unless explicitly requested by the user) → coverage matrix final check |

## 4-Stage Shift-Left QA Loop

QA prevents defects across seams rather than waiting at the end of implementation:
1. **`define` — AC Testability, Ambiguity & Exception Audit**: inspect every `FR`/`NFR`/`GWT` for measurable thresholds, state transitions, and boundary/exception outcomes in `01-define/test-plan.md`; bounce untestable or contradictory criteria back to `pm` before `shape`.
2. **`shape` — Risk-Based Test Layering**: map failure modes to the cheapest falsifying layer (unit / integration / contract / consumer-E2E), lock conservation/metamorphic/AI-golden oracles, `[SEC-n]` auth matrices, and DB dialect fidelity.
3. **`implement` — LLD Unit/Integration + CI Contract Tests**: implementers run LLD-driven unit/integration tests and executable contract tests wired into non-bypassable PR CI before handing off to `qa`.
4. **`verify` — Test-Submission Entry Checklist (提测准入清单)**: verify `## 0` of [templates/test-report.md](templates/test-report.md) FIRST (`契约测试通过` · `受影响单元测试通过` · `关键异常路径已覆盖并追溯到 GWT/AC` · `构建产物可部署`). Any unchecked item bounces immediately back to `implement` without burning `verify` cycles.

## Gotchas

- **Green unit tests, unusable product.** Every key journey `J-n` needs a real consumer-boundary check: a browser for UI, API/CLI/SDK/batch execution for other surfaces. The matrix label **E2E** marks journey-level checks; it does not require every assertion to use a browser, and screenshots are evidence only for UI. `e2e: null` is not acceptable for a UI change (v4 gate `E2E`). Details: [e2e-and-exploratory.md](references/e2e-and-exploratory.md).
- **AI self-confirming example tests hide systematic bugs.** Hand-picked single-input assertions (`assert calc_fee(100) == 3`) often mirror the author's off-by-one or sign mistake. Pair GWT boundary examples with **conservation invariants** (e.g. ledger `Σ debits == Σ credits`, split/refund sum == original principal, paginated union == unpaginated set) and **metamorphic relations** (narrowing filters never grows result set; changing sort order preserves multiset; replaying an idempotent request leaves state and side-effect count unchanged). Details: [case-derivation.md](references/case-derivation.md).
- **Non-deterministic AI/ML features still need hard release gates.** Never test LLM/RAG/agent/ranking outputs with brittle exact-string equality alone, and never waive verification because "AI varies." Separate **deterministic guardrails** (schema parse, citation existence, tool/tenant permission boundary, prompt-injection refusal, token/latency cap — 100% pass) from **probabilistic Golden-Eval gates** (pinned golden dataset + rubric/groundedness/recall floor from NFR, recording model/prompt/seed version and baseline delta). Cross-check domain obligations in [industry-delivery-sops.md](../impl-evidence/references/industry-delivery-sops.md).
- **Scripted tests only find what you imagined.** Run at least one exploratory charter on the riskiest area per L2+ feature and log it in [templates/test-report.md](templates/test-report.md).
- **Events and security controls are first-class test obligations.** With `tracking: yes`, each `EV-n` gets a validation row (fired once, right properties, right identity). When `q_security: yes` or architecture defines `[SEC-n]`, anchor every `[SEC-n]` trust boundary in §1e of `coverage.md` (including direct HTTP bypass of UI hiding and cross-tenant IDOR).
- **The matrix proves mapping only when anchored to real `File:Line` and non-hollow assertions.** `assert True` or HTTP `200` without persisted state/side-effect checks is hollow — G-fresh flags it as `major`.
- **Preconditions must be real state.** A Given that reads data must commit or persist it inside the same test; a case that relies on another test's leftovers passes alone and fails in another order.
- **SQLite silently accepts PostgreSQL syntax (like `NULLS LAST`).** SQLite unit tests do not establish production-dialect correctness for affected SQL behavior — verify on the real DB dialect or mark `[需真库验证]` and track handoff to `sre`.
- **Targeted testing only — full-suite runs are prohibited.** Regression follows change impact (affected modules, callers, shared tables/contracts and journeys); never run the full repository test or E2E suite unless the user explicitly asks for it.
- **Cross-entry parity needs matching content, not matching labels.** For changed preview/detail/copy/download/gesture consumers, use the fixed-object checks in [e2e-and-exploratory.md](references/e2e-and-exploratory.md); local-media claims also require actual bytes and consumption evidence.

## Key decisions

### Deriving test cases & oracles from GWT

For each FR/NFR acceptance criterion ([case-derivation.md](references/case-derivation.md)):
1. **Happy path & state persistence**: Given/When/Then verified at persisted state and downstream side effects, not HTTP status alone.
2. **Three-point boundaries**: in-bounds, **on-boundary**, out-of-bounds (asserting zero side effects on rejection).
3. **Unauthorized & `[SEC-n]` controls**: role swap, scope/tenant swap (`IDOR`), and direct HTTP calls bypassing UI hiding.
4. **Legal & illegal state transitions**: every illegal transition asserts unchanged state + error code + **zero side effects** (inventory/ledger/notifications).
5. **Conservation, metamorphic & AI golden-eval oracles**: domain sum/set invariants for stateful/data logic; golden-set pass-rate + deterministic safety rails for AI/ML paths.

### Trace matrix format (`04-verify/coverage.md`)

| FR/NFR | GWT | 用例 ID | 测试文件:行号 | 层 | 状态 | 备注 |
|---|---|---|---|---|---|---|
| FR-01 | GWT-01.1 | TC-001 | `tests/integration/test_export.py:18` | 集成 | ✅ | |
| FR-03 | GWT-03.1 | — | — | — | ❌ **缺口** | 必须在第 5 节说明原因与阻塞单 |

**Matrix holes are the verify exit condition** — every hole needs a test or a documented exemption with reasoning. Write the matrix to `04-verify/coverage.md` (gate path; not `trace-matrix.md` as the filename) using [templates/trace-matrix.md](templates/trace-matrix.md). `check-matrix.py` verifies every `FR` / `NFR` / `EV-n` id, real `测试文件:行号` paths on disk, and every `J-n` on a row marked **E2E**.

### Environment fidelity

Test environment must match the production properties relevant to the risk; record residual differences ([test-layering.md](references/test-layering.md)). For any SQL feature that varies by dialect, either run against the production DB engine or track `[需真库验证]` to completion with `sre`.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | spec (`FR`/`NFR`, journeys `J-n`) · `01-define/test-plan.md` · `01-define/tracking.md` (`EV-n`) · `02-shape/contract.md` & `security-review.md` (`[SEC-n]`) · implementation evidence · `edge-states.md` (UI) · running app (`app.base_url`) |
| **Output** | define: `01-define/test-plan.md` ([templates/test-plan.md](templates/test-plan.md)) · verify: `04-verify/coverage.md` ([templates/trace-matrix.md](templates/trace-matrix.md)) · E2E gate `e2e` · [templates/test-report.md](templates/test-report.md) · [templates/bug-report.md](templates/bug-report.md) |
| **Source writes** | verify tasks may write assigned test code, fixtures and test-runner configuration through the packet's `source_writes`; inspection-only runs omit it; `define/test-plan` never writes project source. None of this authorizes product-code fixes or a changed business oracle |
| **Downstream** | Defect tickets → implement rework · `04-verify/coverage.md` + `test-report.md` → `qc` |
| **Refuse** | Fixing defects (write tickets, don't fix) · release decisions (→ `qc`) · writing implementation code |

## Self-check

- [ ] `define/test-plan`: AC testability/ambiguity/exception check completed, acceptance IDs, failure modes, cheapest layers, conservation/metamorphic/AI-golden oracles, fixtures/dialect fidelity and pending decisions documented — with zero invented execution results?
- [ ] `verify` entry gate (`## 0. 提测准入核对` in `test-report.md`) verified first — bouncing back to `implement` if contract tests, affected unit tests, exception GWT/AC traceability, or deployable build artifacts are missing?
- [ ] `verify`: every journey `J-n` has an E2E row that actually ran at its consumer boundary (`e2e` never null on UI)?
- [ ] Every matrix row in §1 carries a real `测试文件:行号` on disk (or explicit hole/N/A reason)?
- [ ] `tracking: yes`: every `EV-n` validated; `q_security: yes` / `[SEC-n]`: every security boundary anchored in §1e?
- [ ] L2+ verify: at least one exploratory charter run and logged?
- [ ] Conservation/metamorphic invariants used where example-only assertions could self-confirm implementation bugs; AI paths gated by deterministic rails + golden-eval thresholds?
- [ ] Illegal transitions and rejected inputs assert zero side effects (DB/files/ledger/events)?
- [ ] Defects follow `提交 → 确认 → 修复 → 验证 → 关闭` with severity anchored strictly to observable user/business impact, and escaped bugs record Process-QA seam fixes (`escape.seam_fix` + `verified_by`)?
- [ ] Targeted regression strictly scoped to change impact (no unauthorized full-suite runs), and fixed defects added to regression set?
- [ ] Environment/SQL-dialect fidelity verified or tracked with `sre`?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [e2e-and-exploratory.md](references/e2e-and-exploratory.md) | Journey E2E, shared controls across page themes, shared row heights for in-place sibling views, tracking validation and exploratory heuristics |
| [case-derivation.md](references/case-derivation.md) | Deriving GWT cases, conservation & metamorphic invariants, `[SEC-n]` auth matrices, and AI golden-eval gates |
| [test-layering.md](references/test-layering.md) | Affected regression scope, fixture isolation, unit / integration / E2E split and SQL dialect fidelity |
| [industry-delivery-sops.md](../impl-evidence/references/industry-delivery-sops.md) | Domain-specific verification rules (fintech ledger conservation, multiplayer concurrency, offline sync, AI/LLM safety) |
| [templates/test-plan.md](templates/test-plan.md) | Early risk-based test plan (`01-define/test-plan.md`) |
| [templates/trace-matrix.md](templates/trace-matrix.md) | `04-verify/coverage.md` FR/NFR/J-n/EV-n/SEC-n ↔ `File:Line` matrix |
| [templates/test-report.md](templates/test-report.md) | Verification execution & fidelity report |
| [templates/bug-report.md](templates/bug-report.md) | Reproducible defect ticket |
| `scripts/check-matrix.py` | Mechanical hole & `File:Line` detection invoked by `check-sdlc.sh` on `04-verify/coverage.md` |

> Gotchas based on: `anthropics/skills@41bbe19` (webapp-testing Common Pitfall pattern, 2026-09-03) · a verified production dialect escape (ESC-2)

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
