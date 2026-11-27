# Industry Data & Schema SOPs — 9 Domain Archetypes

Load only the archetype(s) matching the assigned product or feature data scope (system boundaries: [industry-architecture-sops.md](../../architecture/references/industry-architecture-sops.md); implementation & migration verification: [industry-delivery-sops.md](../../impl-evidence/references/industry-delivery-sops.md)). Keep engine-specific syntax aligned with [engine-and-evidence.md](engine-and-evidence.md).

---

## 1. `b2b-saas` — Tenant Isolation, RLS & Exemption Matrix

- **Per-Table Tenancy Classification**: Every new or modified table in `db-spec.md` must declare one explicit class:
  1. `tenant-scoped`: `tenant_id NOT NULL`, included in tenant-local unique constraints `(tenant_id, slug)` and evaluated in composite indexes per actual query predicates.
  2. `platform-exempt`: global system config, public catalog, or cross-tenant operational ledger — requires explicit security justification in `db-spec.md`.
- **Cross-Tenant Referential Integrity**: Never allow a child row in Tenant A to reference a parent ID in Tenant B. Enforce composite foreign keys `(tenant_id, parent_id) -> parent(tenant_id, id)` or PostgreSQL Row-Level Security (`ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` with fail-closed `current_setting('app.tenant_id')` session variable — empty setting returns 0 rows, never all rows).
- **Soft-Delete Active Uniqueness**: Never assume `UNIQUE (tenant_id, email, deleted_at)` prevents duplicate active rows (`NULL != NULL` in standard SQL). Use PostgreSQL partial unique indexes (`WHERE deleted_at IS NULL`) or MySQL active-token/generated columns verified under concurrency.

## 2. `fintech-ledger` — Immutable Double-Entry Ledger & Reconciliation

- **Red Line — Never Mutate Authoritative Balances**: Authoritative wallets, accounts, and clearing balances **MUST NOT** be modeled as a standalone mutable `UPDATE users SET balance = balance - ?` column! Mutable overwrites destroy auditability, hide partial failures, and make double-charge vs legitimate repeat transactions indistinguishable.
- **Immutable Double-Entry Schema**:
  - `accounts(id, tenant_id, account_type, currency CHAR(3), status)` — chart of accounts (user available, user held/escrow, platform revenue, gateway clearing).
  - `journal_batches(id, tenant_id, idempotency_key UNIQUE, biz_type, biz_ref_id, posted_at)` — one atomic financial event.
  - `ledger_postings(id, batch_id FK, account_id FK, direction, amount_minor BIGINT CHECK (amount_minor > 0), currency CHAR(3), created_at)` — **append-only** (`INSERT` only; database privileges/triggers or repository contract forbid `UPDATE`/`DELETE`).
  - **Conservation Invariant**: Within every `batch_id` and `currency`, **`Σ debits == Σ credits`** (or signed `Σ signed_amount_minor == 0`).
- **Transactional Balance Projection**: When low-latency balance reads or overdraft prevention are required, maintain `account_balances(account_id PK, posted_balance_minor, held_balance_minor, version, updated_at)` updated **in the exact same DB transaction** as `ledger_postings` (`CHECK (posted_balance_minor - held_balance_minor >= 0)` for non-credit accounts). `ledger_postings` remains the authoritative truth; corrections post **reversing batches** (`reversal_of_batch_id`), never edits.
- **Minor Units & T+1 3-Way Reconciliation**: Store exact integer minor units (`BIGINT` cents/satoshis) + ISO-4217 `currency` + `fx_rate DECIMAL(18,8)` snapshot. Provide reconciliation queries proving `SUM(ledger_postings) == account_balances` and matching external gateway settlement files (`T+1` 3-way check).

## 3. `ecommerce-marketplace` — 3-Tier Inventory & Order Snapshot Isolation

- **Three-Tier Inventory Invariants**: Model `inventory_items(sku_id PK, warehouse_id, on_hand BIGINT, reserved BIGINT, version BIGINT)` with invariant **`on_hand >= reserved AND reserved >= 0`** (`available = on_hand - reserved` derived or generated). Pair every reservation with `inventory_reservations(id, order_id, sku_id, qty, status, expires_at, UNIQUE(order_id, sku_id))`:
  - Reserve: `UPDATE inventory_items SET reserved = reserved + :q WHERE sku_id = :s AND on_hand - reserved >= :q` + insert `RESERVED` row in same transaction.
  - Ship/Commit: `on_hand = on_hand - :q, reserved = reserved - :q` + mark `COMMITTED`.
  - Cancel/Expire: conditional `status = 'RESERVED' -> 'RELEASED'` + `reserved = reserved - :q` (idempotent against race between payment callback and expiry sweeper).
- **Order & Line-Item Snapshot Isolation**: `orders` and `order_items` must snapshot `title_snapshot`, `sku_attrs_json`, `unit_price_minor`, `tax_rate`, `line_discount_minor`, `line_payable_minor`, and `shipping_address_json` at checkout (`modeling-patterns.md` §4). Never join live `products.price` or `user_addresses` to compute historical order totals or refunds.

## 4. `consumer-social` — Timeline Cursors, Hot Counters & Visibility Staging

- **Cursor Tie-Breakers**: High-write feeds use keyset/cursor pagination `(created_at DESC, id DESC)` backed by matching sort-direction composite indexes — never deep `OFFSET 100000` or timestamp-only cursors that drop rows sharing the same millisecond.
- **Fact vs Hot Counter Separation**: Store interaction truth in append-only deduplicated tables (`post_likes(post_id, user_id, created_at, PK(post_id, user_id))`) and absorb write spikes via sharded `counter_buckets(target_type, target_id, bucket_no TINYINT, count BIGINT)`.
- **Dynamic Visibility Sets**: When feed/catalog `total`, facets, and page share time-dependent or state-dependent predicates (moderation pass, author active, expiry `> NOW()`, media ready), stage once per request in a transaction-scoped snapshot rather than persisting drifting summary counts ([modeling-patterns.md](modeling-patterns.md) §8).

## 5. `ai-agentic` — Run Traces, Tool Idempotency & Vector Metadata

- **Agent Run & Step Auditability**: Model `agent_runs(id, tenant_id, actor_id, prompt_version, model_id, status, total_input_tokens, total_output_tokens, cost_micros, started_at, ended_at)` + `agent_steps(run_id, step_seq, kind, payload_ref, latency_ms, UNIQUE(run_id, step_seq))`.
- **Tool Side-Effect Ledger**: Persist `tool_invocations(id, run_id, step_seq, tool_name, idempotency_key UNIQUE, approval_status, effect_state, external_receipt)` where `effect_state ∈ ('pending', 'succeeded', 'failed', 'in_doubt')` so interrupted runs reconcile external effects instead of re-executing blind mutations.
- **Vector / RAG Chunk Schema**: Every indexed chunk row/metadata must carry `tenant_id NOT NULL`, `acl_principal_ids` or `visibility_scope`, `source_doc_id`, `source_version`, `chunk_seq`, `embedding_model_id`, and `source_updated_at`. Index `(tenant_id, source_doc_id)` for atomic document re-chunking/deletion without cross-tenant leakage.

## 6. `aigc-workbench` — Asset Provenance, Rights Lineage & Staging Receipts

- **Immutable Asset & Lineage Graph**: Separate `media_blobs(sha256 CHAR(64) PK, byte_size BIGINT, mime_type, storage_uri)` from `assets(id, project_id, owner_id, kind, current_blob_sha256, rights_policy, source_channel)` and `asset_lineage_edges(child_asset_id, parent_asset_id, transform_op, params_hash)`. Derived assets deterministically inherit the most restrictive `rights_policy` of their parents unless an authorized license upgrade is recorded.
- **Staging Receipt Lifecycle**: Model upload/generation staging receipts (`receipt_id`, `target_blob_sha256`, `temp_bytes_path`, `state ∈ ('writing', 'staged', 'verified', 'aborted')`, `updated_at`). Cleanup queries delete receipts **only** when `updated_at < NOW() - :grace_interval`, no companion uncommitted `.bytes` handle exists, and the target `media_blobs` row + object digest check pass.
- **User vs System Preference State**: Separate `disabled_by_user BOOLEAN` from `system_channel_available BOOLEAN` in model/provider catalogs so background catalog syncs never overwrite manual user opt-outs.

## 7. `data-crawler` — 3-State Manifests, Full-Identity Dedup & Watermarks

- **Three-State Window Manifest (`missing ≠ empty`)**: Separate collected records from `collection_windows(source, scope_key, window_start, window_end, status, row_count, raw_archive_uri, updated_at, UNIQUE(source, scope_key, window_start))` where `status ∈ ('pending', 'succeeded_non_empty', 'succeeded_empty', 'failed_schema', 'failed_transient')`. `succeeded_empty` (`row_count = 0`) is a valid terminal fact; never represent empty windows by omitting rows.
- **Full-Identity Deduplication Keys**: Composite unique constraints on ingested metrics/items must include **every dimension that scopes the request** `(source, account_id, geo_or_entity_id, metric_code, period_start)` — omitting `geo_or_entity_id` silently overwrites `N` regional responses into 1 row on upsert.
- **Checkpoints & Recoverable Redis State**: Classify Redis keys explicitly ([redis-key-governance.md](redis-key-governance.md), [recoverable-writes.md](recoverable-writes.md)): crawl watermarks, pending leases, and publish intents are **authoritative recovery state** (no `allkeys-lru` eviction, no blind TTL jitter that drops unacknowledged work).

## 8. `regulated-compliance` — PII Vaults, Crypto-Shredding & Legal Hold

- **PII Vault Separation**: Split erasable personal identifiers into `subject_pii(subject_ref PK, tenant_id, encrypted_payload VARBINARY, dek_id, email_blind_idx BINARY(32), erased_at)` while operational, clinical, or financial tables reference only pseudonymous `subject_ref` (no raw name/SSN/phone/email duplicated into audit or event payloads).
- **DSAR Erasure vs Legal Hold**: Model `legal_holds(id, tenant_id, subject_ref, authority_ref, placed_at, released_at NULL)` and `dsar_requests(id, tenant_id, subject_ref, status, blocked_by_hold_id NULL, completed_at)`. When `EXISTS (SELECT 1 FROM legal_holds WHERE subject_ref = :ref AND released_at IS NULL)`, DSAR erasure transitions to `blocked_legal_hold`; otherwise shred `subject_pii` / destroy per-subject DEK while leaving WORM `audit_logs` (append-only, hash-chained `prev_hash + entry_hash`) intact.
- **Maker-Checker Persistence**: Dual-control tables enforce `CHECK (proposer_id <> approver_id)` (or equivalent non-null approval transition constraint) plus immutable `payload_sha256` binding approval to the exact proposed diff.

## 9. `client-iot-localfirst` — SQLite Skipped-Version Migrations & Sync Schemas

- **Sequential Skipped-Version Migration Chain**: Embedded/client SQLite schemas (`PRAGMA foreign_keys = ON`, `PRAGMA journal_mode = WAL`, explicit `busy_timeout`) must maintain a monotonic migration table (`PRAGMA user_version` or `schema_migrations`). Users jump directly across releases (`v1.1 -> v2.0` skipping `v1.2..v1.9`): every intermediate step must preserve existing user rows, rebuild tables safely (`CREATE TABLE new -> INSERT SELECT -> DROP old -> RENAME`) inside explicit transactions, and never rely on dev-only `DROP & CREATE`.
- **Local-First Sync & Conflict Columns**: Synced local tables include `id UUID/ULID`, `server_version BIGINT`, `local_dirty BOOLEAN NOT NULL DEFAULT 0`, `deleted_at` tombstone (hard-deleting locally loses the delete event before sync!), and a companion `local_mutation_outbox(mutation_seq PK, client_mutation_id UNIQUE, entity_type, entity_id, op, patch_json, base_server_version, state)` + `sync_conflicts(id, entity_type, entity_id, local_json, server_json, resolved_at)` so offline edits never vanish silently.
