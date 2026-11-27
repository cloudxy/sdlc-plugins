---
name: "schema"
description: "Use this skill when the spawn packet names dba or $schema. Do NOT load in /sdlc or for Service/Repository code."
when_to_use: "Use this skill when the spawn packet names hat dba or the user types $schema / names this hat. Do NOT use from parent /sdlc. Do NOT use for Service/Repository code or API shapes."
---

# Schema — business invariants, data models and safe evolution

Job: make persisted facts correct, auditable, and performant at the product's actual workload. Keep this capability separate from `architect`'s API/system decisions and `data-warehouse-engineer`'s analytical definitions. Reuse established models; a new feature does not require redesigning the domain.

## Task selection

Task IDs and outputs come from `workflow/registry.json`.

| Task | Work and completion evidence |
|---|---|
| product/bootstrap | Reverse-engineer `domain-model.md` and `erd.dbml` from named code/migration/runtime versions; mark inferred or inaccessible facts |
| dba/model | Business grain/invariants → relationships/types → access patterns → applicable roadmap stress test → `db-spec.md` and `schema.dbml`; proposed until accepted |
| dba/optimize | Reproduce a workload issue; compare plans and representative timings before/after; state limits and index/write-cost trade-offs |
| dba/migration | Own destructive, `expand-contract`, backfill, engine/RLS, or shared-table migrations; deliver atomic `{migration + ORM metadata + package manifest}` with compatibility, zero-count data checks, and recovery rehearsal |

A design task without database access ends with a testable plan and `unverified` claims, never fabricated `EXPLAIN` or migration output. A migration task needs explicit file/environment permissions; no production execution is implied.

## Procedure

1. **Frame grain, invariants & domain archetype.** Read spec/architecture data semantics and the existing model at a named revision, plus matching domain rules in [industry-data-sops.md](references/industry-data-sops.md) (aligned with [industry-architecture-sops.md](../architecture/references/industry-architecture-sops.md)). State each fact's single owner (DIE/SSOT), one-sentence row grain, lifecycle, retention, sensitivity, per-table tenancy/exemption class, and business invariants. Resolve missing business meaning with `pm`; reuse authorized decisions.
2. **Model relationships, snapshots & ledgers.** Separate historical snapshots (`price_at_purchase`, `fx_rate`, address) from live foreign-key references. **Financial red line**: authoritative wallets, accounts, and clearing balances must use **append-only double-entry `ledger_postings` (`Σ debits == Σ credits`)** in integer minor units (or exact fixed-scale `DECIMAL`) + currency + transactional balance projection + T+1 3-way reconciliation — **never** a standalone mutable `UPDATE users SET balance = balance - ?` overwrite. Do not turn every transient/derived value into a stored column.
3. **Select engine-true keys, types & active uniqueness.** Choose surrogate, natural, composite, or UUID keys for the actual engine/version ([engine-and-evidence.md](references/engine-and-evidence.md)). Make null semantics, UTC timestamps vs local dates, and legal/illegal state transitions explicit. Enforce active-row uniqueness with engine-verified constraints (e.g. PostgreSQL partial unique index `WHERE deleted_at IS NULL`), never assuming nullable `deleted_at` blocks duplicates.
4. **Derive bounded access patterns.** Evaluate predicates, sort directions (`ASC`/`DESC`), selectivity, and write amplification across both Top-N high-frequency queries and low-frequency high-risk integrity checks. Leftmost `tenant_id` indexes aid performance; tenant authorization still requires server/RLS enforcement.
5. **Stress-test known evolution (OCP vs YAGNI).** Walk roadmap `Next/Later` items ([extensibility-patterns.md](references/extensibility-patterns.md)) without inventing speculative EAV tables; document costly future transitions honestly rather than promising all evolution is additive.
6. **Plan compatible rollout & DBA/Backend ownership.** Use [expand-contract.md](references/expand-contract.md) whenever `N-1` and `N` code coexist. **Ownership boundary**: destructive DDL, `expand-contract`, backfills, and shared-table alterations belong exclusively to `dba/migration`; routine additive slice-local tables implemented by `backend` must match accepted `schema.dbml` 1:1 with zero unilateral drift. Distinguish code rollback, schema `down`, and business-data recovery (RPO / forward-fix).
7. **Handoff.** Deliver approved semantics and versioned schema to `backend`, invariants/dialect/race cases to `qa`, and bounded rollout/recovery steps to `sre`; align vocabulary with `data-warehouse-engineer` without copying metric formulas into OLTP tables.

## Source authority and baseline

Declare whether migrations/models or DBML are the schema authority for the project. Feature `db-spec.md` holds change rationale, invariants, and semantic annotations — not a second manually maintained column catalog (DIE). Promote product `domain-model.md` / `erd.dbml` current facts only after implementation evidence, keeping code state distinct from deployed environments. Return product delta rows to the manager.

## Gotchas and checks

- SQL syntax, NULL uniqueness, JSON indexing, and online DDL locking are engine/version-specific ([engine-and-evidence.md](references/engine-and-evidence.md)). `EXPLAIN ANALYZE` executes the statement: run only in scoped environments with resource/time limits and safe data.
- **Stage dynamic visibility sets once per request (DIE/SSOT).** When list `total`, facets, and page share a current-visibility predicate (latest row, expiry, rights, moderation, available media), materialize that visible set once per request and read all three from it — never store a drifting summary counter ([modeling-patterns.md](references/modeling-patterns.md) §8). Counters fit only when every mutation updates the count atomically in the same transaction.
- **Ship migration, ORM/metadata index definitions (`ASC`/`DESC`), and package manifests (e.g. `pyproject.toml`) atomically**, running targeted schema-parity and package-layout checks in the same change.
- **Reconcile shared dev-DB temporary revisions non-destructively**: inspect existing tables first and rewind only the revision pointer while preserving concurrent sessions' tables/rows — never blindly `DROP` another session's table.
- **Guard idempotent staging/recovery receipts** with grace-period expiry + absence of companion uncommitted `.bytes` + target blob digest verification before cleanup.
- **Classify Redis keys before setting TTL or eviction** ([redis-key-governance.md](references/redis-key-governance.md), [recoverable-writes.md](references/recoverable-writes.md)): reconstructible caches require jittered TTLs; authoritative pending/journal/watermark recovery state must never use `allkeys-lru` or blind expiry.
- **Keep discovery, verification & documentation proportional on additive/ODS tables**: when upstream code or a pinned fixture already fixes table/column names and the manager's brief records verified DB/alembic baselines, reuse those pinned facts instead of repeating identical projections or multi-turn config probes; batch independent read-only DB/code checks into one command; do not `WebFetch` official manuals for textbook engine fundamentals (e.g., MySQL 64-char identifier limit or VARCHAR length-byte boundary) or inspect DB driver/C-extension internals for doc notes. Prefer `python3 <PLUGIN_ROOT>/scripts/tools/schema_parity.py` for static migration/ORM/DBML/fixture parity checks, keep additive round-trip verification scripts compact (≤120 lines), keep `db-spec.md` focused on non-obvious trade-offs/invariants rather than duplicating `schema.dbml`, record only commands + exit codes + key assertion lines in `migration-review.md` (never pasting multi-ten-KB raw logs), and allow at most one factual fix pass after checks pass (no repetitive prose-polish loops).

## References & templates — load only applicable methods

- Industry data archetypes (fintech ledger, 3-tier inventory, RLS, AIGC lineage, crawler 3-state, DSAR/legal-hold, SQLite skipped-version sync): [industry-data-sops.md](references/industry-data-sops.md).
- Domain boundaries & known variation: [domain-modeling.md](references/domain-modeling.md), [extensibility-patterns.md](references/extensibility-patterns.md).
- Hierarchies, audit/history, money, snapshots, tenancy, state machines, concurrency, visibility staging: [modeling-patterns.md](references/modeling-patterns.md).
- Engine/evidence rules: [engine-and-evidence.md](references/engine-and-evidence.md); MySQL 8 `EXPLAIN` details only: [explain-reading.md](references/explain-reading.md).
- Safe evolution & recoverable state: [expand-contract.md](references/expand-contract.md), [redis-key-governance.md](references/redis-key-governance.md), [recoverable-writes.md](references/recoverable-writes.md).
- Deliverables & diagrams: [db-spec](templates/db-spec.md), [schema.dbml](templates/schema.dbml), [domain-model](templates/domain-model.md), [erd.dbml](templates/erd.dbml), [migration-review](templates/migration-review.md), [er-diagram.md](references/er-diagram.md).
- Independent review uses [role-quality.md](references/role-quality.md) ("Expert Bar vs Mediocre Order-Taker + Second-Order Scan").
