# Professional review criteria

Read the section for the producing role during execution and independent review. These role-specific criteria were moved from agent identities; methods and self-checks remain in this skill.

## data-warehouse-engineer

- A **product-level metric tree**: north star → drivers → guardrails, each with formula, source events/tables, grain, dimensions, exclusions and owner; feature metrics are added to that tree, never defined beside it.
- A layered model (ODS → DWD → DWS → ADS) fed by tracking events and OLTP, with conformed dimensions (user, time, content, channel) shared across subjects.
- A **user tag system**: fact, rule and model tags with logic, refresh cadence, owner, consumers and privacy class — computable from `tracking-plan.yaml` events, so every growth segment is reproducible.
- Idempotent ETL with quality assertions (uniqueness, nulls, ranges, row-count deltas) and lineage.
- Analytics never hurt production: a written storage decision (read replica vs OLAP store) with the trigger to move.
