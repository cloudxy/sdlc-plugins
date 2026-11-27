# Industry Delivery, Ownership & Failure-Injection SOPs

Load for the active slice's domain archetype alongside your primary `lane_file` (`ui | api | ai | model`). Cross-references: [industry-architecture-sops.md](../../architecture/references/industry-architecture-sops.md) and [industry-data-sops.md](../../schema/references/industry-data-sops.md). **Targeted verification only**: run only the targeted unit, integration, parity, and failure-injection checks covering the touched slice — full-suite test runs remain prohibited unless explicitly requested.

---

## Cross-Lane Ownership Contracts (Mandatory)

### 1. DBA vs Backend Migration & ORM Ownership Contract

| Change Category | Exclusive Owner | Delivery & Verification Obligation |
|---|---|---|
| **Destructive DDL, `expand-contract`, data backfill, shared/core table alteration, engine/partition/RLS tuning, or standalone `dba/migration`** | **`dba`** | Delivers an **atomic unit**: `{migration script + ORM/metadata index & constraint alignment + distribution package manifest (e.g. pyproject.toml data-files)}` plus isolated compatibility (`up/down/up` where data-safe), zero-count backfill verification, and recovery rehearsal. `backend` **MUST NOT** author destructive DDL or alter shared tables unilaterally. |
| **Routine additive slice-local tables/indexes inside an authorized `backend` ticket (`source_writes`)** | **`backend`** (consuming accepted `dba/model`) | Must match approved `02-shape/schema.dbml` and `db-spec.md` **1:1** (column names, types, nullability, defaults, unique keys, FKs, and exact index sort directions `ASC`/`DESC`), update ORM metadata + package manifest atomically in the same commit, and paste `SHOW CREATE TABLE` / `alembic check` / schema-parity exit `0` in `impl-evidence.md`. Missing column/index/constraint → **stop and escalate to `dba`**. |

- **Shared Dev-DB Non-Destructive Rule**: Before running local migrations on a shared dev/formal DB, inspect existing tables/revisions; if another session left an uncommitted temporary revision, rewind only the revision pointer while preserving existing tables/rows — **never blindly `DROP` another session's table**.

### 2. Miner → Warehouse `data/tags.yaml` Proposal Handoff

- Per `workflow/registry.json` write permissions, **`miner` does NOT directly edit `data/tags.yaml`**.
- Whenever a `miner` segmentation or scoring model produces user/entity segments or scores consumed by `ops`, CRM, or downstream analytics, `miner` records a **structured tag proposal** in its evidence / `model-card.md` (`tag_id`, entity grain, `< :asof` SQL/feature logic, value enum/thresholds, refresh cadence, staleness SLA, and business action owner) and hands it off to **`data-warehouse-engineer`**, who owns registering and governing `data/tags.yaml`.

---

## 9 Industry Archetypes — Implementation & Failure-Injection Obligations

### 1. `b2b-saas`
- **Implementation**: Bind `tenant_id` strictly from authenticated server context into every repository query/mutation; UI cross-workspace views (`all projects`) route item mutations using `item.project_id` / `item.tenant_id`, never ambient page state.
- **Required Targeted Proof**: (a) Cross-tenant negative test (`Tenant A` actor reading/mutating/exporting `Tenant B` ID returns `403`/`404` with zero DB mutation); (b) Role-downgrade / token-revocation rejection test; (c) Cross-page bulk selection parity test if bulk actions exist.

### 2. `fintech-ledger`
- **Implementation**: Integer minor-unit math only (zero `float`); write `journal_batches` + append-only `ledger_postings` (+ transactional `account_balances` projection) inside one DB transaction; keep payment/payout HTTP calls strictly outside the DB transaction using persistent `Idempotency-Key` + Three-State (`Success / Fail / In-Doubt`) handling.
- **Required Targeted Proof**: (a) Ledger conservation assertion (`Σ debits == Σ credits` per batch); (b) Parallel duplicate webhook/request race (`asyncio.gather` → 1 batch, identical response, zero overdraft); (c) **`In-Doubt` timeout injection**: simulate gateway read timeout → verify record enters `in_doubt`/`processing` and queries upstream receipt before retry (zero blind double-charge/payout); (d) Reversal-only refund test (zero `UPDATE`/`DELETE` on `ledger_postings`).

### 3. `ecommerce-marketplace`
- **Implementation**: Atomic conditional stock reservation (`WHERE on_hand - reserved >= :qty`); checkout snapshots item price/title/tax/allocated-discount into `order_items`; penny-remainder allocation preserves `sum(item_payable_minor) == order_payable_minor`.
- **Required Targeted Proof**: (a) Concurrent oversell race (`10` parallel checkouts on `stock = 3` → exact `3` succeed, `reserved == 3`, zero negative `available`); (b) Reservation TTL sweeper vs late payment callback race; (c) Post-checkout catalog price mutation test proving historical order total & partial-refund math stay unchanged.

### 4. `consumer-social`
- **Implementation**: Keyset cursor pagination `(created_at, id)`; Cache-Aside delete-after-commit + jittered TTL + singleflight on hot keys; single-pass transaction-scoped visibility staging when `total`/facets/page share dynamic visibility; optimistic UI updates paired with `onError` rollback.
- **Required Targeted Proof**: (a) **Brownout / Redis-unavailable injection**: mock cache/recommendation failure → core feed/detail degrades cleanly without 500 or N+1 query explosion; (b) Concurrent insert cursor walk (zero duplicate or dropped items across pages); (c) UI first-load skeleton vs background-refresh retention + optimistic rollback check.

### 5. `ai-agentic`
- **Implementation**: Pin prompt + model + `eval-set-v<n>` versions in config/repo; enforce retrieval-layer `tenant_id`/ACL metadata filter before context assembly; isolate untrusted user data in delimited prompt blocks + strict output schema validation; enforce hard `max_steps`, `max_tokens`, timeout, and tool-sandbox/HITL token verification outside the LLM; implement 3-tier degradation (`primary -> backup -> rules/abstention`).
- **Required Targeted Proof**: (a) Reproducible `eval-set` run comparing cheapest baseline vs candidate on identical frozen version (reporting all rounds including negative ones); (b) Adversarial/prompt-injection & cross-tenant retrieval denial test; (c) **Streaming & Breaker injection**: simulate upstream timeout / step-loop / mid-stream disconnect → verify typed SSE `event: error` + fallback activation + upstream cancellation.

### 6. `aigc-workbench`
- **Implementation**: Separate source reference, content-addressed media bytes, and preview/Range-playback URLs; register every transform in the canonical lineage & rights resolver; guard staging receipt cleanup with grace-window + active-`.bytes` check + target digest verification; keep `disabled_by_user` distinct from system channel sync.
- **Required Targeted Proof**: (a) **Lineage round-trip test**: feed derived output (crop/split/stitch/remix) into downstream consumer → verify inherited rights pass without `422`; (b) Staging GC safety test (uncommitted `.bytes` or digest mismatch is never deleted; disk-floor guard stops cleanly); (c) Media `HEAD` / `Range` `206` byte-serving verification; (d) Catalog sync test preserving manual user disables.

### 7. `data-crawler`
- **Implementation**: Return 3 distinct extraction states (`non-empty`, `valid empty []`, `missing/malformed None`); key merges/upserts on full request identity; log every drop/skip reason at `INFO`+; pair transient retries with jittered budgets and permanent conditions with terminal markers; scope pause/circuit-breaker strictly to the failing source/account.
- **Required Targeted Proof**: (a) Captured valid vs invalid payload guard test (proving hygiene guards neither pass malformed data nor reject 100% of real traffic); (b) `N` same-metric multi-geo/account merge collision test (`N` inputs → `N` distinct persisted records); (c) Valid `data=[]` test persisting `succeeded_empty` without infinite retry; (d) Mid-write / ambiguous-ack crash recovery test.

### 8. `regulated-compliance`
- **Implementation**: Envelope-encrypt sensitive fields via KMS/DEK interface; enforce `proposer_id != approver_id` + payload hash on Maker-Checker transitions; emit attributable tamper-evident audit records; implement `legal_hold` pre-check on DSAR erasure; strip all PII/PHI/secrets from logs, traces, URLs, and error responses.
- **Required Targeted Proof**: (a) Self-approval & tampered-payload rejection test (`403`/`409`); (b) Log/response PII leak scan across success and `4xx`/`5xx` branches; (c) **DSAR vs Legal-Hold test**: subject under active `legal_hold` blocks erasure auditable-cleanly; unheld subject shreds PII vault while WORM audit/ledger rows remain intact and verifiable.

### 9. `client-iot-localfirst`
- **Implementation**: Whitelist IPC/JSBridge commands, origins, and canonicalized file paths; ship sequential SQLite migrations + local outbox + tombstones; enforce CLI stdout (`--json`) vs stderr separation and deterministic exit codes; handle OS permission `denied` and `revoked-in-settings` states explicitly.
- **Required Targeted Proof**: (a) **Skipped-version migration test**: upgrade populated `v1.1` SQLite fixture directly to current `v2.0` → exit `0`, zero row/constraint loss; (b) Bridge negative test (`../` path escape & unlisted IPC command rejected); (c) CLI `--json` stdout parse + non-zero exit code check (for CLI/SDK slices); (d) Offline cold-start / sync-conflict / permission-revoked walkthrough (mark hardware-only capabilities `unverified` when only simulator/previewer is available).
