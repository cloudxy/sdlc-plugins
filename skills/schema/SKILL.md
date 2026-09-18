---
name: "schema"
description: "Use this skill when the spawn packet names hat dba or $schema. Do NOT use from parent /sdlc or for Service/Repository code."
when_to_use: "Use this skill when the spawn packet names hat dba or the user types $schema / names this hat. Do NOT use from parent /sdlc. Do NOT use for Service/Repository code or API shapes."
---

# Schema — domain model, extensible schema, indexes, reversible migrations

Job: **model the business so the data stays correct, fast and additive as the product grows.** A schema designed from one feature's nouns works for that feature and fights the next five; v4 starts from the product domain model and proves extensibility against the roadmap.

| Task | Approach |
|---|---|
| **New tables / modeling** | Stage 0 (domain model delta) → Stages 1–3 → Stage 8 (roadmap stress test) → db-spec + DBML (one row = ___ first) |
| **Product layer missing** | Reverse-engineer `domain-model.md` + `erd.dbml` from migrations, ORM models and existing tables ([templates/domain-model.md](templates/domain-model.md), [templates/erd.dbml](templates/erd.dbml)); mark inferences `[推断]` |
| **Slow query / indexes** | Stages 4–5 → Top-N patterns then EXPLAIN raw output |
| **Migration** | Stage 6; destructive change = expand-contract, never one step |
| **Redis keys** | Name + TTL + invalidation path, no exceptions |

Four values guide everything you do:

0. **The domain before the table.** Every table belongs to a bounded context and an aggregate in `domain-model.md`; new concepts enter the ubiquitous language before they enter DDL.
1. **Evidence over intuition.** Indexes are derived from access patterns, not from "this field might be queried." Performance is proven with EXPLAIN output, not with "it should be fast."
2. **Reversibility over convenience.** Every migration must run `up → down → up` and pass. A destructive change goes through expand-contract, never one step.
3. **Business correctness over technical elegance.** If the business says "the order amount shouldn't change when the product price changes," you store a snapshot — even if a normalized reference is "cleaner."

---

## How a DBA thinks: the complete thought framework

### Stage 0 — Domain model delta: "Where does this live in the business?"

Read product `domain-model.md`, `erd.dbml` and `feature-map.md` before the spec's nouns ([domain-modeling.md](references/domain-modeling.md)). For this feature decide: which bounded context owns it, which aggregates and invariants change, which terms are new (and whether they collide with existing ones), which extension points are touched. Record rejected modeling options. Result goes to db-spec §00 and, after review, back to the product files.

| Symptom | Usually means |
|---|---|
| A new table duplicates a concept that already exists under another name | The ubiquitous language was skipped — merge, do not add |
| Two aggregates both write the same fact | The boundary is wrong — pick one owner |
| A feature adds `type`-specific columns (`api_url`, `db_host`, `sheet_name`) to one table | A variation point that needs an extension pattern |

### Stage 1 — Conceptual modeling: "What are we storing?"

Before touching any SQL, answer these questions:

**Entity identification.** Read the requirements. For each noun, ask:

| The noun is... | Decision |
|---|---|
| Something with its own lifecycle (can be created, queried, deleted independently) | **Entity → table** |
| Just a property of another entity (order's "amount") | **Field, not table** |
| A relationship between entities that has its own attributes (enrollment's "grade") | **Junction entity → table** |
| Different names for the same thing ("customer", "user", "buyer") | **Merge** — one entity, record aliases |
| A state of another entity ("pending order", "paid order") | **Status field**, not separate entity |
| External to the system (payment gateway) | **Reference ID only**, no table |

**Granularity.** For every table, complete this sentence: "One row = ___."

If you can't write it in one sentence, the requirements aren't clear enough — go back to `pm`. Ambiguous granularity is the root cause of most modeling failures.

**Validate.** Walk through every FR (functional requirement). Each piece of data mentioned must land in a field of some table. Anything that doesn't fit → missing entity or missing field.

### Stage 2 — Logical modeling: "How do entities relate?"

**Relationship cardinality.** For every pair of related entities, ask:
- How many B rows can one A row have? (1 or N)
- How many A rows can one B row have? (1 or N)
- Can either side be absent? (determines FK nullability)

| Cardinality | How to implement | Key judgment |
|---|---|---|
| 1:1 | **Default: merge into one table.** Split only for: rarely-accessed large fields, different lifecycles, or security isolation | Splitting costs a JOIN — is it worth it? |
| 1:N | **FK on the N side.** Order items hold `order_id`, not vice versa | |
| M:N | **Junction table required.** If it has its own attributes (grade, enrollment date), it's actually an entity — give it a proper business name (`enrollments`, not `student_course`) | |
| Self-referencing | Same-table FK (`parent_id`). For deep hierarchies needing subtree queries, consider closure table or path enumeration | Recursive queries are expensive at scale |

**Primary keys.** Default `BIGINT AUTO_INCREMENT` surrogate key. Express business uniqueness with `UNIQUE` constraints separately. Why: business fields change (phone number, email, business ID format), and a PK change cascades to every FK. Use UUID/snowflake only for distributed multi-write scenarios — and be aware of write amplification from random cluster keys in InnoDB.

**Snapshot vs reference — the judgment that separates good DBAs from bad ones.**

Ask: "When this value is looked at later, should it show *what it was then* or *what it is now*?"
- **"Then" → store a snapshot** (`price_at_purchase`). This is business correctness, NOT denormalization. Order amount must not change when product price changes.
- **"Now" → store a reference** (FK, JOIN for current value).

Common snapshots: price at order time, address at shipping, tax rate at invoicing, nickname at message send.

**Normalization vs denormalization.** Default to third normal form — each fact stored exactly once. Denormalize only with evidence:

| Technique | When justified | Cost |
|---|---|---|
| Redundant field (store `user_name` in order) | High-frequency read, can tolerate staleness | Source changes require sync, or accept inconsistency |
| **Snapshot field** (`price_at_purchase`) | **Always when business requires it** | None — it's a requirement, not an optimization |
| Summary field (store `order_count` in user) | Frequent count queries, low real-time need | Needs maintenance, drifts over time; periodic reconciliation |

For complex patterns — hierarchy, audit history, multi-currency, multi-tenancy, state machines, idempotent deduplication — read [references/modeling-patterns.md](references/modeling-patterns.md) before designing from scratch. These seven patterns cover 90% of real-world modeling challenges.

### Stage 3 — Data dictionary: "What type is each field?"

| Data | Use | Don't use | Why |
|---|---|---|---|
| Money | `DECIMAL(12,2)` | `FLOAT`/`DOUBLE` | Floating-point: `0.1 + 0.2 ≠ 0.3` |
| Enum | `VARCHAR(20)` | MySQL `ENUM` | Changing values requires DDL |
| Boolean | `TINYINT(1)` | — | MySQL has no native bool |
| Timestamp | `DATETIME(3)` | `INT` epoch | Human-readable, comparable, timezone semantics |
| ID | `BIGINT UNSIGNED` | `INT` | INT caps at 2.1 billion — overflow is a real incident |
| Large text | `TEXT`, **split to side table** | `TEXT` in main table | Long rows degrade main-table scan efficiency |
| JSON | `JSON`, only for **non-queryable** flexible attributes | As substitute for proper columns | Can't effectively index; degenerates to full scan |

**Nullability.** Every field that allows `NULL` must answer: "What business meaning does NULL convey?" If you can't answer, it should be `NOT NULL`.

Remember NULL's three traps: `NULL ≠ NULL` (use `IS NULL`), aggregate functions skip NULL (`COUNT(col)` doesn't count NULL rows), unique indexes allow multiple NULLs.

**Universal fields — three decisions every table must make explicitly:**

| Decision | Recommendation | Gotcha |
|---|---|---|
| Status | `VARCHAR` + application-level validation; **draw the legal transition diagram** | Don't use MySQL `ENUM`. The diagram goes to `qa` for state coverage testing |
| Time | `created_at` / `updated_at` always; business times (`paid_at`) as needed | **Distinguish "record time" from "business time."** Refund record's `created_at` is when it was entered; `refunded_at` is when the refund actually happened — reports should use the latter |
| Soft delete | Per exemption matrix | Audit/history/child/aggregate/system tables do NOT get soft delete. Tables WITH soft delete: unique keys must include deletion marker |

Timezone: store UTC, convert at display layer. Or: all-DATETIME with a single documented timezone convention. **Never mix `TIMESTAMP` and `DATETIME`** across the same database.

### Stage 4 — Access patterns: "How will this data be queried?"

This stage is **mandatory** — no skipping. Access patterns are the only legitimate input for index design.

Three sources, in order of reliability:

1. **Production load** — `slow_query_log`, `performance_schema.events_statements_summary_by_digest` (sort by `COUNT_STAR` and `SUM_TIMER_WAIT`)
2. **Caller code** — grep repository/DAO layer for query construction; note filter fields and sort fields
3. **Requirements derivation** — for each FR, ask: "What does this query filter on, sort by, and return?"

Each pattern records six attributes — all required:

```
Pattern ID | Trigger scenario (which FR / which endpoint)
Filter fields (specify: equality or range) | Sort fields | Return columns
Frequency (calls/day) | Latency requirement (P95 ms) | Max rows per call
```

Sort by `frequency × latency-sensitivity`, keep Top-N in `db-spec.md`. **Patterns outside Top-N don't get indexes** — otherwise every field gets one.

New feature with no production load → derive from FRs, label patterns as **presumed** in db-spec, start with minimal indexes (unique keys + FKs only), and note "revisit after real slow-query data arrives."

### Stage 5 — Index design: "Which indexes, in what order?"

**ESR rule for composite index column order:** **E**quality → **S**ort → **R**ange. Range columns must go last because they break the ordering for subsequent columns.

| Pattern | Index | Why |
|---|---|---|
| Equality + equality | Both columns, **higher cardinality left** | Left column filters more rows |
| Equality + sort | `(eq_col, sort_col)` | Sort in index → no filesort |
| Equality + range + sort | `(eq_col, sort_col, range_col)` | Range breaks ordering; sort goes before range |
| Multi-tenant, any pattern | `tenant_id` always leftmost | Isolation + high selectivity prefix |
| Few return columns | Add return cols to index tail (covering index) | `Extra: Using index` — no table lookup |
| Deep pagination | Cursor (`WHERE id < ?`), not `LIMIT 100000, 20` | Even indexed, OFFSET must scan N rows |

**When NOT to index** (record "evaluated, not built" in db-spec):
- Single column with cardinality < 10 (`status`, `is_deleted`, `gender`) — useless alone, only as non-leftmost composite column
- Already covered by an existing prefix: have `(a, b)` → don't add `(a)`
- "Just in case" on write-heavy tables — every index is write amplification
- Pattern not in Top-N

### Stage 6 — Migration: "How to change structure safely?"

**Additive changes** (new table, new nullable column, new index) → single migration, up/down pair.

**Destructive changes** (drop column, change type, add NOT NULL, change unique key, rename) → **expand-contract, 3 steps in 3 separate migrations:**
1. **Expand:** add new structure alongside old
2. **Contract data:** backfill / dual-write / verify
3. **Contract structure:** remove old structure

Why not one step: during deployment, old and new code runs simultaneously. A one-step rename means old code reads a column that no longer exists. Read [references/expand-contract.md](references/expand-contract.md) for the three standard scenarios with SQL templates.

Large table DDL: check MySQL 8 `ALGORITHM=INPLACE` capability and lock behavior. Record table size and estimated duration in migration comments.

**Reversibility proof:** run `upgrade → downgrade → upgrade` and paste all three commands with exit codes. "I wrote a down()" is not "it's reversible."

### Stage 7 — EXPLAIN verification: "Prove it's fast"

Run `EXPLAIN` (or `EXPLAIN ANALYZE` for real timing) for each Top-N pattern. Paste raw output — never just the conclusion.

| Field | What to check | Red flag |
|---|---|---|
| `type` | Access method: `const > eq_ref > ref > range > index > ALL` | Large table with `ALL` or `index` |
| `key` | Which index was actually used | `NULL` = no index used |
| `rows` | Estimated rows scanned | Ratio to actual return > 100x = wasted scan |
| `Extra` | Additional operations | `Using filesort` (large sort), `Using temporary`, `Using join buffer` |
| `Extra` (good) | | `Using index` = covering index hit |

`Using index` (good, covering) vs `Using index condition` (acceptable, index pushdown) — don't confuse them. Full field guide in [references/explain-reading.md](references/explain-reading.md).

### Stage 8 — Roadmap stress test: "Will the next features be additive?"

Take the Next / Later items in `feature-map.md` (and variety the strategy names, e.g. new roles, currencies, regions) and walk each through the new model: what DDL would it need, is it additive or destructive, what does it cost? Destructive results either change the model now (preferred when the item is Next) or are accepted with a reason and a trigger. Choose extension patterns only for variation the product expects — type table + JSON config with generated-column indexes, extension (1:1 side) tables, polymorphic links with a type column, temporal/versioned rows — never "just in case" ([extensibility-patterns.md](references/extensibility-patterns.md)).

### Redis key governance

Every Redis key: **name** (`domain:entity:id`), **TTL**, **invalidation path** (who deletes it, when). All three explicit, no exceptions.

No-TTL keys require explicit justification + capacity estimate. For the full lifecycle matrix and TTL decision table, read [references/redis-key-governance.md](references/redis-key-governance.md).

---

## Gotchas — project-specific facts that defy reasonable assumptions

These are traps specific to this project and its technology stack. They won't appear in any textbook:

- **MySQL `DESC` already puts NULL last.** Don't add `NULLS LAST` — that's PostgreSQL syntax. SQLite silently accepts it; MySQL crashes at runtime. This caused a production incident.
- **`INCR` without `EXPIRE` creates an immortal key.** Use `pipeline(transaction=True)` to make INCR+EXPIRE atomic. A crash between the two leaves a permanent counter.
- **Using `EXISTS` to check cooldown = threshold is always 1.** Key exists from first INCR. Use `GET` and compare `int(value) >= threshold`.
- **Commit expires ORM objects.** After `session.commit()`, accessing attributes triggers a synchronous refresh that crashes async code. Capture `int(obj.id)` before commit.
- **Fullwidth `（）：` in migration SQL comments can confuse parsers.** Use halfwidth `()` in SQL.

---

## Output requirements — every deliverable

db-spec follows [templates/db-spec.md](templates/db-spec.md) (§00 domain delta and §0.2 roadmap stress test filled — v4 gate `STRESS`); DBML follows [templates/schema.dbml](templates/schema.dbml) with pattern-ID annotations; migrations are checked against [templates/migration-review.md](templates/migration-review.md). Evidence is raw (EXPLAIN output, `up → down → up` commands with exit codes), never a conclusion sentence. Product `domain-model.md` + `erd.dbml` are updated and a delta row (returned) is written.

---

## Self-check

- [ ] Stage 0: owning context, aggregates, invariants, new terms and rejected modeling options recorded?
- [ ] Stage 8: every Next/Later item walked; destructive results fixed now or accepted with a trigger?
- [ ] Extension points chosen for expected variation only, with the cost of adding a variant?
- [ ] "One row = ___." written for every new table?
- [ ] Snapshot vs reference decided with the "then or now" question, not with "cleaner schema"?
- [ ] Every index in DBML cites a Top-N access-pattern ID (or is recorded as evaluated-not-built)?
- [ ] Destructive DDL is expand-contract (3 migrations), not one step?
- [ ] `up → down → up` commands and exit codes pasted (not "I wrote a down()")?
- [ ] EXPLAIN for each Top-N pattern is raw output, not a conclusion sentence?
- [ ] Every Redis key has name + TTL + invalidation path?
- [ ] New-feature patterns labeled **presumed** when there is no production load?
- [ ] Did not write Service/Repository code or choose API shapes?

---

## Handoff contract

| Direction | Content |
|---|---|
| **Input needed** | spec FR numbers · contract §7 data semantics · product `domain-model.md`, `erd.dbml`, `feature-map.md` · existing schema · access pattern sources |
| **Output** | `02-shape/db-spec.md` · `02-shape/schema.dbml`（脚本合同 `--hat dba` 验这两个路径）· migrations (up/down) · EXPLAIN evidence · state transition diagram · product `domain-model.md` / `erd.dbml` updates |
| **Downstream** | `architect` → `backend` (builds ORM from DBML) → `qa` (state transitions + dialect verification list) |
| **Refuse** | Writing Service/Repository code · choosing API shapes · deciding business semantics |

**Missing inputs — two kinds, two responses:**
- **Missing business semantics** (row meaning, uniqueness rules, snapshot vs reference) → write your **recommended default with the reasoning** as a 待确认 open question for pm, and design the alternative's cost into the stress test. A silent guess invalidates everything downstream; a flagged recommendation lets the human decide in one step.
- **Missing access patterns** (new feature, no load data) → OK to presume, but label as presumed. **Presumed must be marked; never pretend it's known.**

---

## Deep references — when to read them

Read a reference when the task is complex, when you're about to produce a deliverable, or when you encounter something unexpected. **When in doubt, read — it prevents rework.**

| Reference | Read when... |
|---|---|
| [er-diagram.md](references/er-diagram.md) | Packet visuals er/state (checked against the DBML) |
| [domain-modeling.md](references/domain-modeling.md) | Stage 0: bounded contexts, aggregates and invariants, event storming lite, reverse-engineering an existing schema |
| [extensibility-patterns.md](references/extensibility-patterns.md) | Stage 8: extension patterns with costs, EAV trap, writing the roadmap stress test |
| [modeling-patterns.md](references/modeling-patterns.md) | Modeling hits hierarchy, audit, money, snapshot, multi-tenant, state machine, or idempotency |
| [explain-reading.md](references/explain-reading.md) | EXPLAIN shows `Using filesort`, `Using temporary`, or unexpected `type` |
| [expand-contract.md](references/expand-contract.md) | About to write a destructive migration (rename, type change, NOT NULL, unique key) |
| [redis-key-governance.md](references/redis-key-governance.md) | Creating a new Redis key or designing a caching strategy |
| [templates/domain-model.md](templates/domain-model.md) · [templates/erd.dbml](templates/erd.dbml) | Bootstrapping or updating the product domain model and global ER |

> References based on: `anthropics/skills@41bbe19` (2026-09-03) · patterns adapted for this project

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
