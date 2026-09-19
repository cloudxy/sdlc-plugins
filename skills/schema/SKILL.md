---
name: "schema"
description: "Use this skill when the spawn packet names hat dba or $schema. Do NOT use from parent /sdlc or for Service/Repository code."
when_to_use: "Use this skill when the spawn packet names hat dba or the user types $schema / names this hat. Do NOT use from parent /sdlc. Do NOT use for Service/Repository code or API shapes."
---

# Schema — business invariants, data models and safe evolution

Job: make persisted facts correct and usable at the product's actual workload. Keep this capability separate from architecture's API/system decisions and warehouse's analytical definitions. Reuse established models; a new feature does not require redesigning the domain.

## Task selection

Task IDs and outputs come from `workflow/registry.json`.

| Task | Work and completion evidence |
|---|---|
| product/bootstrap | Reverse-engineer domain-model and ER from named code/migration/runtime versions; mark inferred or inaccessible facts |
| dba/model | Business grain/invariants → relationships/types → access patterns → applicable roadmap impact → db-spec and DBML; models are proposed until accepted |
| dba/optimize | Reproduce a workload issue; compare plans and representative timings before/after; give limits and index/write-cost trade-offs |
| dba/migration | Design or implement the explicitly assigned migration scope; compatibility, backfill, data checks and recovery rehearsal appropriate to the operation |

A design task without database access ends with a testable plan and unverified claims, not fabricated EXPLAIN or migration output. A migration task needs explicit file/environment permissions; no production execution is implied.

## Procedure

1. Read spec/architecture data semantics and the existing model at a named revision. State each fact's owner, row grain, lifecycle, retention, sensitivity and business invariants. Resolve genuinely missing business meaning with PM; reuse already authorized decisions.
2. Map relationships, cardinality and optionality. Names alone do not prove two entities are identical; contexts may use different models of a person/order. Separate historical snapshots from current references. Do not require every transient/derived requirement value to become a stored column.
3. Select keys and types for the actual engine/version and requirements. Stable natural/composite keys, surrogate keys and UUIDs are choices, not universal bans. Money needs exact units, currency, precision and rounding (decimal or integer minor units where appropriate). Null semantics, timezones, date/time distinctions and state transitions must be explicit.
4. Derive access patterns for every new/changed model, including new features with no production load (label estimates). Indexes serve constraints, risky low-frequency operations and observed/predicted queries. Do not exclude an important pattern merely because it is outside Top-N. Index order depends on predicates, ordering, selectivity, engine and the rest of the workload; tenant isolation is an authorization/data constraint, not proof from a leftmost index column.
5. Compare expected roadmap changes only where relevant; unknown future work remains unknown. Prefer justified incremental changes, and record costly future changes rather than promising all evolution will be additive.
6. Plan compatible evolution and recovery using [expand-contract.md](references/expand-contract.md). Distinguish rollback of code, schema and business data. Test on an appropriate isolated engine/data set. Raw execution plans describe access strategy; they do not alone prove latency or recovery.
7. Handoff approved semantics and versioned schema to implementers; give QA invariants/dialect cases and SRE migration/recovery obligations. Collaborate with warehouse on vocabulary and generated dictionary references, without copying metric formulas into table design.

## Source authority and baseline

Declare whether migrations/models or DBML are the schema authority for this project. DBML is the proposed design or a versioned view when implementation is authoritative; ER SVG and the generated dictionary are derived views. Feature db-spec contains the change rationale and semantic annotations, not a second manually maintained column catalog. Promote product domain-model/ER current facts only after implementation evidence, and distinguish deployed environment from code state. Return product delta rows to the manager.

## Gotchas and checks

- SQL syntax, NULL uniqueness, JSON indexing and online DDL behavior are engine/version-specific. Read [engine-and-evidence.md](references/engine-and-evidence.md) before applying a platform example.
- An index hit is not a performance verdict; a deliberate scan can be correct. `EXPLAIN ANALYZE` executes the statement: use a scoped environment, time/resource limits and safe data.
- A nullable deletion marker in a unique key may permit duplicate live rows. Verify the chosen engine's active-row uniqueness behavior and concurrency, rather than trusting an index name.
- A successful down migration may restore columns but lose business data; backups count as recovery only when restore and post-backup writes are addressed.
- Before completion check: owner/grain/invariants; applicable access patterns; versioned model; compatible rollout and real recovery scope; raw evidence or explicit unknowns; downstream owners; no invented business decision.

## References — load only applicable methods

- Domain and known variation: [domain-modeling.md](references/domain-modeling.md), [extensibility-patterns.md](references/extensibility-patterns.md).
- Relationships, history, money, tenancy, concurrency: [modeling-patterns.md](references/modeling-patterns.md).
- Engine/evidence selection: [engine-and-evidence.md](references/engine-and-evidence.md); MySQL plan details only: [explain-reading.md](references/explain-reading.md).
- Migration: [expand-contract.md](references/expand-contract.md), [migration-review template](templates/migration-review.md).
- Redis only when used: [redis-key-governance.md](references/redis-key-governance.md).
- Deliverables: [db-spec](templates/db-spec.md), [schema.dbml](templates/schema.dbml), [domain model](templates/domain-model.md), [product ER](templates/erd.dbml), [ER drawing](references/er-diagram.md).
- Independent review uses the same [criteria](references/role-quality.md).
