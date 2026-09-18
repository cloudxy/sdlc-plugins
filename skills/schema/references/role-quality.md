# Professional review criteria

Read the section for the producing role during execution and independent review. These role-specific criteria were moved from agent identities; methods and self-checks remain in this skill.

## dba

- Starts from the **product domain model** (bounded contexts, aggregates, invariants, ubiquitous language); this feature's schema is a reviewed **delta** to `erd.dbml`, never an island of new tables.
- **Roadmap stress test**: walks the Next/Later items of `feature-map.md` through the model and shows each is additive — or names the cost and why it is acceptable now.
- **Deliberate extension points** chosen for variation the product already expects (type tables, extension tables, JSON attributes with generated columns, polymorphic links, temporal/versioned rows) — never "just in case".
- Correctness first: a one-row-equals sentence per table, snapshot vs reference decided, uniqueness and invariants enforced by constraints, status transitions drawn.
- Access patterns drive indexes and the storage choice (relational / KV / search / columnar); EXPLAIN output and `up → down → up` runs are the evidence.
