# QA Excellence & Review Rubric

Apply alongside [coverage-matrix SKILL.md](../SKILL.md) when producing or reviewing `01-define/test-plan.md`, `04-verify/coverage.md`, `test-report.md`, defect tickets and test suites.

## 1. Stage-Scoped Deliverables

| Task / Stage | Excellence Bar | Reject (`major` / `blocker`) |
|---|---|---|
| `define/test-plan` (`01-define/test-plan.md`) | Maps `FR`/`NFR`/`J-n`/`EV-n`/`[SEC-n]` to failure modes, cheapest falsifying layers, conservation/metamorphic/AI-golden oracles, dialect needs and open contract questions | Invented pass/fail execution results, finished matrix, or premature source writes |
| `verify/risk-based-tests` (`04-verify/coverage.md`) | Every covered row cites a real `测试文件:行号` on disk; every `J-n` runs at its consumer boundary (`e2e` never null on UI); `EV-n`, `[SEC-n]` and ≥1 L2+ exploratory charter logged | Missing `File:Line`, `e2e: null` on UI change, silent matrix holes, or unlogged skips |
| Defect tickets (`bug-report.md`) | Deterministic clean-state repro, trace ID, GWT/contract oracle citation, independent fix re-run, and permanent `TC-R<nnn>` regression entry | Guessing business intent instead of asking `pm`/`architect`, or fixing product code inside `qa` |

## 2. Oracle Strength (Defeating Hollow & Self-Confirming Tests)

- **State + zero-side-effect assertions**: Positive cases verify persisted DB/file/event state rather than HTTP `200` alone. Rejected inputs and illegal state transitions assert three things together: unchanged state, contract error code, and **zero side effects** (no deducted stock, no ledger posting, no orphan file/event).
- **Conservation invariants**: Financial, inventory, quota, pagination and rollup logic assert path-independent conservation (`Σ debits == Σ credits`, `balance_before - balance_after == net_delta`, paginated union == unpaginated set with `0` duplicates, `Σ child_rows == parent_total`).
- **Metamorphic relations**: Complex filter, search, sort, pricing and serialization paths assert relational invariants (`filter(A ∧ B) ⊆ filter(A)`, sort-order multiset invariance, `parse(format(x)) == x`, idempotent key replay leaves state and side-effect count unchanged).
- **Probabilistic AI / LLM Golden-Eval gates**: Separate 100%-required deterministic rails (schema validity, citation existence, tool/tenant auth boundary, prompt-injection refusal, token/latency cap) from version-pinned Golden-Eval pass-rate floors tied to NFR thresholds.

## 3. Environment Fidelity, Security & Targeted Regression

- **Real browser & production SQL dialect**: UI layout, strict CSP (`style-src`), console errors and cross-scope/cross-page actions are checked in a real browser (never JSDOM alone). Dialect-sensitive SQL (`NULLS LAST`, `FOR UPDATE`, JSON/date ops, isolation) runs against the production DB engine or is tracked to closure with `sre`.
- **Direct-HTTP `[SEC-n]` checks**: Authorization tests exercise role swaps, cross-tenant IDOR (`tenant_id`/resource ID tampering), and direct HTTP requests bypassing hidden frontend controls.
- **Targeted-only regression**: Scope regression strictly to impacted modules, callers, shared tables/contracts and affected journeys — never run unauthorized full-suite sweeps.
