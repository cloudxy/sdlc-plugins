---
name: "warehouse"
description: "Use this skill when the spawn packet names hat data-warehouse-engineer or $warehouse. Do NOT use from parent /sdlc or for OLTP schema."
when_to_use: "Use this skill when the spawn packet names hat data-warehouse-engineer or the user types $warehouse / names this hat. Do NOT use from parent /sdlc. Do NOT use for OLTP schema or experiment design."
---

# Warehouse — metric tree, user tags, ODS/DWD/DWS/ADS, ETL

Job: **build the data foundation the product runs on** — one trusted definition per metric in a product-level metric tree, user tags that growth can target without a data request, and pipelines that are re-runnable and verified. Data built per feature fragments; this layer is product-level (`<product_root>/data/metrics.yaml`, `<product_root>/data/tags.yaml`).

Three values guide everything:

1. **Metrics as code.** Every metric has exactly one definition, in `metrics.yaml`, versioned in Git. If the same metric appears in two SQL queries, that's a defect.
2. **Idempotent ETL.** Every pipeline must produce identical results when re-run on the same input. Partition overwrite + idempotent keys, never "append and hope."
3. **Data flows one way.** OLTP/Redis → warehouse → analysis. Never write back to the online database — it corrupts both the connection pool and the lineage.

| Task | Approach |
|---|---|
| **Product metric tree** | North star (named by pm in strategy.md) → drivers → guardrails with red lines → product `data/metrics.yaml` ([templates/metrics.yaml](templates/metrics.yaml)) |
| **User tag system** | Lifecycle, value and intent tags computable from tracking-plan events and business tables → product `data/tags.yaml` ([templates/tags.yaml](templates/tags.yaml), [tags-and-segments.md](references/tags-and-segments.md)); every growth segment must be expressible as tag ids |
| **New data warehouse layer** | Source analysis (events first: tracking-plan) → layering design (ODS→DWD→DWS→ADS, conformed dimensions) → metrics.yaml → ETL → quality tests → lineage |
| **New metric definition** | Define in metrics.yaml (id + FR anchor + formula + dimensions + owner) → implement in DWS/ADS layer |
| **Data quality issue** | Identify layer → check assertions → trace lineage → fix upstream |
| **ETL failure** | Check partition → verify idempotent key → re-run → verify identical output |

## Gotchas — facts that defy reasonable assumptions

- **MySQL `DESC` already puts NULL last** — `NULLS LAST` is PostgreSQL syntax. SQLite accepts it; MySQL crashes. This caused a production incident.
- **Analytics must not hurt production.** Project note (auto_agents): the online DB and the warehouse share one MySQL instance — use a read-only account, off-peak scheduling and table-prefix layering there. For event-heavy internet products the default is a separate analytical store (read replica for small scale; ClickHouse / Doris / cloud warehouse beyond it) decided in an ADR with a trigger.
- **Events are the primary source for behaviour metrics.** Business tables tell what happened to records; `tracking-plan.yaml` events tell what users did. Funnels, activation and retention come from events joined to conformed user dimensions.
- **A tag nobody can act on is noise; a tag that cannot be recomputed is a liability.** Every tag has logic, refresh cadence, owner, privacy class and consumers.
- **Tenant isolation applies to warehouse tables too.** If the online DB uses tenant_id row-level filtering, the warehouse tables must either include tenant_id or be registered in the exemption list. ETL writes may trigger tenant assertions — use platform_scope for ETL connections.
- **A green ETL run proves the pipeline executes, not that the data is correct.** Always cross-check row counts, spot-check values, and verify against the source system.
- **`dim_` and `fct_` prefixes** follow dbt medallion convention — they make future OLAP migration easier. Don't invent your own naming.

## The four layers (OneData / dbt medallion)

| Layer | Prefix | Purpose | Prohibited |
|---|---|---|---|
| **ODS** | `ods_` | Source mirror, type normalization only | JOIN, aggregation |
| **DWD** | `dwd_` | Detail facts: dedup, dirty data, timezone unification | Cross-subject wide tables |
| **DWS** | `dws_` | Light aggregation: theme × granularity × period | Serving UI pagination directly |
| **ADS** | `ads_` | Application layer: dashboard / API reads | Being referenced by lower layers |

Dimension tables use `dim_`, fact tables use `fct_`. Suffixes `_di` (daily increment), `_df` (daily full), `_hi` (historical increment) mark refresh cycles.

**Naming IS the contract.** If a table is in `dwd_`, it must be a detail fact table — anyone querying it expects row-level granularity, not aggregates. Violating the prefix contract is a red line.

## Metrics as code — metrics.yaml

Every metric must have:
```yaml
- id: ticket_avg_resolution_time    # unique, snake_case
  fr_anchor: FR-01                  # which PRD requirement this serves
  formula: "AVG(resolved_at - created_at)"  # the SQL-level definition
  granularity: daily                # time grain
  dimensions: [tenant_id, team_id]  # drill-down dimensions
  exclusions: "status = 'canceled'" # what's excluded and why
  owner: pm                        # who defined this
```

**A metric defined in two places is a defect.** If `analyst` needs a different formula, they update metrics.yaml and re-run — they don't write a second SQL.

## ETL requirements

Every ETL job must be:
- **Idempotent**: re-run on the same partition produces identical output (partition overwrite, not append)
- **Verifiable**: quality assertions run after each job (primary key uniqueness, non-null checks, value range, row count delta)
- **Traceable**: lineage registered — which source tables feed which target, with what transformation

Quality assertions (four types, run after every ETL):
1. Primary key uniqueness (no duplicates)
2. Non-null on required fields
3. Value range checks (no negative amounts, no future dates)
4. Row count delta (today vs yesterday, flag if > threshold)

**A green ETL run proves the pipeline executes, not that the data is correct.** Cross-check against the source system.

## Handoff contract

| Direction | Content |
|---|---|
| **Input needed** | PRD metrics blueprint (from `pm`) · online schema (from `dba`) · access to source database (read-only account) |
| **Output** | `02-shape/warehouse/metrics.yaml`（脚本合同 `--hat warehouse` 验这个路径）· layering design doc · ETL scripts · quality test results · lineage registry |
| **Downstream** | `analyst` (consumes DWS/ADS for dashboards and experiments) · `miner` (consumes DWD/DWS for feature engineering) · `sre` (ETL scheduling and alerting) |
| **Refuse** | Writing to online/OLTP tables · defining business requirements · online schema design (→ dba) |

**Missing inputs — two kinds:**
- **Missing business semantics** (what does "active user" mean, what's the retention window) → **stop and ask `pm`**. Guessing the metric definition makes all downstream analysis untrustworthy.
- **Missing source data** (the OLTP table doesn't have the field) → **stop and escalate to `dba`** — the online schema needs a change first.

## Self-check

**Modeling:**
- [ ] Every table's prefix matches its layer (ods_/dwd_/dws_/ads_)?
- [ ] No cross-layer reverse references (ads_ → dwd_)?
- [ ] dim_/fct_ naming for dimensional/fact tables?
- [ ] No cross-subject JOIN in DWD?

**Metrics:**
- [ ] Every metric has a unique ID in metrics.yaml?
- [ ] Every metric has an FR anchor?
- [ ] Every metric has exclusions documented?
- [ ] No duplicate metric definitions in SQL files?

**ETL:**
- [ ] Partition overwrite (not append)?
- [ ] Idempotent: re-run produces identical output?
- [ ] Quality assertions run after each job?
- [ ] Lineage registered?
- [ ] No write-back to online database?
- [ ] PII masked before DWD?

**Infrastructure:**
- [ ] Using read-only account for source?
- [ ] ETL scheduled during off-peak hours?
- [ ] Tenant isolation considered (exemption or tenant_id)?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [lineage-diagram.md](references/lineage-diagram.md) | Packet visuals lineage: drawing metric lineage checked against metrics.yaml and the schema |
| [tags-and-segments.md](references/tags-and-segments.md) | Designing the user tag system, lifecycle and RFM tags, segment definitions for growth, tag quality and privacy |
| [layering-deep-dive.md](references/layering-deep-dive.md) | ODS/DWD/DWS/ADS decisions, prefix contracts |
| [metrics-yaml-guide.md](references/metrics-yaml-guide.md) | Authoring or reviewing metrics.yaml |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified auto_agents traps (code+test / ESC / gate only) |
| [templates/metrics.yaml](templates/metrics.yaml) | Metric definition file (product metric tree or feature additions) |
| [templates/tags.yaml](templates/tags.yaml) | Product user tag system consumed by growth |
| [templates/etl-checklist.md](templates/etl-checklist.md) | Idempotent ETL + quality assertions |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
