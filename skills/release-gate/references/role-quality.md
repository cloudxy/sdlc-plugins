# QC Release-Gate Excellence & Review Rubric

Apply alongside [release-gate SKILL.md](../SKILL.md) when producing or auditing a `release-opinion.md` decision (`ship` / `conditional` / `block`).

## 1. Scope, Verdict Parseability & Authority Precision

| Obligation | Excellence Bar | Reject (`major` / `blocker`) |
|---|---|---|
| Target & candidate identity | Names candidate SHA/version, environment, and `local_verified` vs `release_ready`; requires `06-deliver/readiness.md` before `release_ready` | Treating `local_verified` as production-ready, missing `readiness.md` on `release_ready`, or claiming deployment/announcement permission |
| Single-choice `RELEASEOPINION` line | Unambiguous `结论：放行`, `结论：有条件放行`, or `结论：不放行` line matching gate parser | Leaving all three options on `结论：`, or hedging with "基本可以 / 风险可控 / looks good" |
| Producer independence | Independent completeness audit without re-doing `reviewer` line-by-line review or authoring fixes/tests | Approving own artifacts, patching code, rewriting test cases, or altering gate exit codes |

## 2. Six-Point Completeness Rigor

1. **Mechanical requirement & control reconciliation**: Cross-check PRD `FR`/`NFR`, tracking `EV-n` and security `[SEC-n]` IDs 1:1 against `04-verify/coverage.md` (`File:Line` anchored), counting raw `✗ [SDLC-…]` lines rather than trusting prose summaries.
2. **Role & design artifact completeness**: Reconcile participating roles against `state.yaml` and `02-shape/contract.md` (UI changes lacking `02-shape/edge-states.md` = immediate block).
3. **Implementing slice traceability**: Confirm every `FR` maps to at least one implementing ticket/slice.
4. **Post-fix gate freshness**: Verify every `fixed` finding cites a commit SHA AND re-run gate fingerprints on the final candidate SHA (code edited after gates ran = block).
5. **Deterministic gate fingerprints**: Require verbatim command + exit code + timestamp for `test`, `lint`, `build`, `migration` and `e2e` (`e2e` never null on UI).
6. **Journeys & multi-hat acceptance**: Confirm consumer-boundary E2E ran on every `J-n`, and check `04-verify/accept-pm.md`, `accept-design.md` (UI) and `accept-growth.md` (when applicable): any `不通过` blocks; `有条件通过` requires human-accepted conditions with named owners.

## 3. Non-Waiver & Risk-Authority Escalation

- **Zero silent waivers by `qc`**: `qc` never waives `blocker`/`major` findings or failed gates on its own. Unresolved `blocker`/`major` or failed gates mandate `结论：不放行` unless an authorized human risk owner signs an explicit waiver naming criterion, version, environment, risk owner, reason, compensating control and expiry/recheck trigger (legal/security/constitutional red lines cannot be waived without authority to override them).
- **Observable residual risk**: Never accept an unmonitored failure mode ("rely on user complaints") without requiring monitoring or blocking/conditional remediation.
