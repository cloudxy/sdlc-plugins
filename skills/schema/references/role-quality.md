# DBA review criteria

Single source of procedure: [schema](../SKILL.md). Judge invariant preservation, workload fit, rollout compatibility, and real data recovery for the assigned task (`product/bootstrap`, `dba/model`, `dba/optimize`, `dba/migration`). Never demand live `EXPLAIN ANALYZE` on a design-only task without DB access, fabricate roadmap requirements, or equate schema `down` exit `0` with business-data restoration.

## Expert Bar vs Mediocre Order-Taker

| Dimension | Expert DBA Bar | Mediocre Order-Taker Anti-Pattern |
|---|---|---|
| **Grain, Snapshots & Ledger Truth** | Explicit one-sentence row grain; snapshots historical price/tax/address facts; models financial balances via **append-only double-entry postings (`Σ debits == Σ credits`)** + integer minor units + transactional projection | Modeling tables 1:1 from UI screens; using `FLOAT` or mutable `UPDATE users SET balance = balance - ?` for money; joining live catalog prices onto historical orders |
| **Tenancy, Uniqueness & Compliance** | Explicit per-table `tenant-scoped` vs `platform-exempt` matrix + composite tenant FKs/RLS; engine-verified active-row uniqueness; PII vault separation + `legal_hold`-aware DSAR | Assuming nullable `deleted_at` in `UNIQUE(tenant_id, slug, deleted_at)` blocks duplicates; relying solely on app `WHERE` clauses or leftmost index columns as security proof |
| **Workload, Staging & Redis** | Derives indexes from predicates + sort directions (`ASC`/`DESC`); stages dynamic visibility predicates once per request ([modeling-patterns.md](modeling-patterns.md) §8); separates reconstructible Redis cache from sole recovery state | Blindly adding single-column indexes; maintaining drifting summary tables for expiry/rights-filtered totals; applying `allkeys-lru` or short TTL jitter to sole pending/journal keys |
| **Evolution & Atomic Handoff** | Multi-step `expand-contract` for destructive changes; batched idempotent backfill with `COUNT(*) == 0` proof; ships `{migration + ORM metadata + package manifest}` atomically; preserves shared dev-DB tables | Single-migration `RENAME`/`DROP`/`ADD NOT NULL` under rolling deploy; omitting `DESC` or `pyproject.toml` packaging; `DROP`ping concurrent dev-session tables |

## Task-Specific Review Gates

- **`product/bootstrap` & `dba/model`**: Current deployed facts vs proposed feature DBML kept distinct; every nullable column states its exact `NULL` business meaning; rejected index candidates documented; Next/Later roadmap stress test avoids EAV anti-patterns.
- **`dba/optimize`**: Before/after plans and representative timings recorded on named engine/version/dataset; intentional small-table or batch scans explicitly justified rather than masked.
- **`dba/migration`**: Exclusive owner of destructive/shared-table changes; separates DDL files from batched resumable backfill scripts; documents exact irreversible cutover point, RPO, and staging receipt grace-window verification.

## Second-Order Scan (Run Before Sign-Off)

1. **N-1 / N Coexistence**: While old app replicas and new app replicas run simultaneously against the migrated schema, which `INSERT`/`SELECT` fails or writes `NULL`?
2. **Concurrent Race & Replay**: If two identical webhooks, checkouts, or workers hit simultaneously — or a reply drops after commit — does a DB constraint serialize them safely?
3. **Rollback vs Data Loss**: If `contract` or a bad deploy rolls back after 2 hours of live traffic, where do those 2 hours of new business writes go (RPO / forward-fix / reversal)?
4. **10x Volume & Skew**: At 1-year row growth or single-tenant skew, which table needs partitioning/archival, sharded counters, or keyset cursors instead of `OFFSET`?
5. **Archetype Completeness**: Are applicable domain invariants in [industry-data-sops.md](industry-data-sops.md) (fintech 3-way reconciliation, 3-tier inventory, crawler 3-state manifest, SQLite skipped-version upgrades) explicitly satisfied?

## Immediate Return-for-Rework Triggers

- Modeling authoritative financial balances with mutable `UPDATE ... SET balance` or `FLOAT` instead of append-only double-entry postings + integer minor units.
- Shipping a migration whose index sort directions (`ASC`/`DESC`), constraints, or package manifest (`pyproject.toml`) diverge from ORM metadata or `schema.dbml`.
- Bundling expand, backfill, and contract into a single deployment step when `N-1` and `N` replicas coexist, or claiming `down` restores dropped business data without proof.
- Fabricating `EXPLAIN ANALYZE` or migration execution output when no database environment was accessible.
