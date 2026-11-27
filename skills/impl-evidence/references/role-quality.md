# Implementer professional review criteria

Read the section for the producing role (`frontend`, `backend`, `algo`, `miner`) during execution and independent review alongside [SKILL.md](../SKILL.md) and [industry-delivery-sops.md](industry-delivery-sops.md). Targeted checks + replayable consumer evidence beat full-suite test theatre.

## Expert Bar vs Mediocre Order-Taker (Shared Engineering Baseline)

| Principle | Expert Implementer Bar | Mediocre Anti-Pattern |
|---|---|---|
| **Boundary & State Modeling** | **Parse, Don't Validate** at ingress; discriminated unions make illegal states unrepresentable; narrow props/DTOs (ISP); zero `a.b.c.d()` train-wrecks (LoD) | Passing raw `dict`/ORM models across layers; boolean flag soup (`isLoading && isError`); mutating shared globals |
| **DIE vs AHA & Statelessness** | Canonical SSOT for visibility predicates, limits, error codes, and tokens (DIE); diverging actor flows kept separate (AHA); **100% process-stateless backend** across horizontal workers | Copy-pasting SQL filters across list/count/export; storing session/progress/rate-limits/locks in module-level `dict` or `RLock` |
| **Resilience & Ownership** | Bounded queries/timeouts/retries/budgets + Three-State (`Success / Fail / In-Doubt`) handling; escalates contract/GWT/schema gaps to `architect` / `pm` / `dba` | Unbounded queries or blind non-idempotent retries; silently inventing columns, error codes, or weakened GWT assertions |

## Role-Specific Criteria

### `frontend` (`lane_file: ui`)
- Reads **why** first: journey `J-n`, spec §2 core value, final prototype `02-shape/prototypes/final/` (`data-component` IDs + state routes), `design-system.md` tokens, and `edge-states.md`.
- Implements all 6 states (loading skeleton vs background refresh, initial empty vs filtered empty, `code`-switched error with `trace_id` + recovery action, permission, offline, extreme boundary data) using tokens (`python3 PLUGIN_ROOT/skills/impl-evidence/scripts/check-frontend.py` exits `0`), semantic a11y/focus restoration, and URL/query-cache state ownership (never copying server state into local `useState`).
- Routes cross-scope/multi-project item actions by `item.project_id` / `owner_id` (never ambient page context) and keeps bulk-action selection scope consistent across pages.
- Walks the slice **against the real backend**, captures breakpoints via `ui-evidence.sh`, visually inspects PNGs side-by-side against the final prototype (including signature moment), verifies `tracking.md` events, and records `03-impl/T-<n>-integration.md`.

### `backend` (`lane_file: api`)
- **Contract & Functional Core first**: publishes contract examples/mock early; isolates complex pure domain math/rules (Functional Core, zero I/O, explicit clock) from thin transactional/I/O orchestration (Imperative Shell); enforces strict CQS (`GET`/probe = zero side effects or billing).
- Enforces transaction boundaries (external HTTP/MQ strictly outside DB tx; outbox/idempotency key + Three-State `In-Doubt` reconciliation), single-pass visibility staging when `total`/facets/page share dynamic predicates, and cold-start subprocess import cleanliness.
- Respects **DBA vs Backend Migration Ownership**: destructive/expand-contract/shared-table DDL belongs exclusively to `dba`; authorized additive slice-local models match `schema.dbml` 1:1 (including index `ASC`/`DESC` and package manifest) with verbatim parity output.
- Verbatim targeted test evidence covers rollback, idempotency race, concurrent write (`rows == 0`), and external timeout/brownout, plus masked structured logs (`trace_id`, zero PII/secrets).

### `algo` (`lane_file: ai`)
- Supports full lifecycle (`implement/T-<n>`, `implement/explore`, `implement/evaluate`, `implement/diagnose`, `implement/fix`): builds/pins a versioned 5-layer stratified `eval-set-v<n>` (frozen `test` split, ≥80% inter-annotator agreement) **before** claiming any quality metric.
- Benchmarks cheapest rules/non-AI baseline first; changes **one variable per round** and preserves all rounds (including negative iterations); separates retrieval (`Recall@k` with pre-retrieval `tenant_id`/ACL filter) from generation faithfulness + citation verification.
- Enforces untrusted-input delimiters, strict output schema validation, hard token/step/cost circuit breakers, tool-sandbox/HITL boundaries outside the prompt, and a tested 3-tier degradation chain (`primary -> backup -> rules/abstention`).

### `miner` (`lane_file: model`)
- Frames the **decision action, capacity cap, and asymmetric error cost** with `pm` before modeling; selects metrics matching capacity (`Precision@K`, `lift`, `PR-AUC`, calibration — never raw accuracy on imbalanced targets).
- Enforces ironclad **as-of discipline** (`< :asof` in every SQL aggregation, interval gap before label window, train-only fit statistics, Top-10 feature 3-question leakage audit) and deployment-matched temporal/group splits with rolling-window variance.
- Delivers Top-10 FP/FN bad-case taxonomy, honest ceiling/failure boundaries, and passing offline-online feature parity (`check_feature_consistency`).
- **Warehouse Tag Handoff**: never edits `data/tags.yaml` directly; delivers a complete segment/tag specification proposal (grain, `< :asof` logic, refresh SLA, thresholds, action owner) in its evidence / `model-card.md` for `data-warehouse-engineer` to register in `data/tags.yaml`.

## Second-Order Scan (All Implementers)

1. **Horizontal Scale & Reload**: What breaks on F5 browser refresh, back/forward navigation, or 2+ backend worker processes?
2. **Timeout `In-Doubt` & Partial Failure**: If the network drops 1ms after the server commits or calls an upstream provider, what does retry produce?
3. **Boundary & Drift**: Did any validation limit, enum, visibility filter, or token get hardcoded in a second place instead of referencing SSOT?
4. **Targeted Honesty**: Do the pasted commands + exit codes prove the exact touched behavior and consumer surface without full-suite waste or mock-only illusions?
