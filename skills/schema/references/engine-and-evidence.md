# Engine-specific decisions and evidence

Record database/version, extension/configuration, migration tool, authoritative schema revision and test environment. MySQL examples elsewhere are examples, not defaults for PostgreSQL, SQLite, document stores or native persistence.

For index choices evaluate actual predicates/order, data distribution, read/write cost and supported index kinds. Equality-sort-range is a useful candidate heuristic, not a law. Low-cardinality partial/hot-state queries may benefit from indexes; existing prefix indexes can have different size/constraint roles. Measure before dropping them. See [PostgreSQL multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html).

Enforce the intended uniqueness scope and NULL behavior. For PostgreSQL, partial unique indexes can constrain active rows; NULLS NOT DISTINCT is a version-dependent alternative with different semantics. For MySQL, design an appropriate generated-key/constraint strategy and verify concurrent inserts. App-only unprotected checks do not enforce uniqueness. See [PostgreSQL CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html).

EXPLAIN estimates a plan; real timings need representative data, warm/cold/cache conditions, concurrency, units and bounds. ANALYZE actually executes, so it is not automatically safe for production or mutating statements. [MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.0/en/explain.html). The bundled check-explain helper is a limited MySQL table-format heuristic, not an engine-neutral performance certificate; declare intentional scans and assess actual objectives separately.

ORM expiration, SQL parser behavior and Redis command patterns depend on the installed configuration; verify the real code and version rather than importing another project's incident as a universal rule.

The tabular EXPLAIN checker now fails empty/unrecognized input and reads named columns. Its scan budget is diagnostic; it does not verify runtime performance or support every engine/format. Use a project-specific verifier for other plans.
