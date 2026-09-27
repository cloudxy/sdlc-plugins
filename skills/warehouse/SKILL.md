---
name: "warehouse"
description: "Use this skill when the spawn packet names hat data-warehouse-engineer or $warehouse. Do NOT use from parent /sdlc or for OLTP schema."
when_to_use: "Use this skill when the spawn packet names hat data-warehouse-engineer or the user types $warehouse / names this hat. Do NOT use from parent /sdlc. Do NOT use for OLTP schema or experiment design."
---

# Warehouse — metric tree, user tags, layered models, ETL

Job: **build the data foundation the product runs on** — one trusted definition per metric in a product-level metric tree, user tags that growth can target without a data request, and pipelines that are re-runnable and verified. Data built per feature fragments; this layer is product-level (`<product_root>/data/metrics.yaml`, `<product_root>/data/tags.yaml`).

Three values guide everything:

1. **Metrics as code.** Every metric has exactly one definition, in `metrics.yaml`, versioned in Git. SQL and dashboards may reference the same metric ID; independently redefining its semantics is the defect. If the project already has a semantic catalog, metrics.yaml indexes that authoritative definition instead of duplicating it.
2. **Idempotent ETL.** Every pipeline must produce identical results when re-run on the same input. Choose partition replacement, merge/upsert or immutable append plus deduplication from source semantics and the required replay boundary.
3. **Data flows one way.** OLTP/Redis → warehouse → analysis. Reverse ETL is a separate, explicitly approved sink contract with access, rate, idempotency and ownership controls; ordinary analytics jobs cannot mutate OLTP.

| Task | Approach | Output |
|---|---|---|
| **Product metric tree** (`warehouse/metrics`, product bootstrap) | North star (named by pm in strategy.md) → drivers → guardrails with red lines ([templates/metrics.yaml](templates/metrics.yaml)) | product `data/metrics.yaml`; feature delta `02-shape/warehouse/metrics.yaml` |
| **User tag system** (`warehouse/tags`) | Lifecycle, value and intent tags computable from tracking-plan events and business tables ([templates/tags.yaml](templates/tags.yaml), [tags-and-segments.md](references/tags-and-segments.md)); every growth segment must be expressible as tag ids. A tags-only request does not require invented metrics | product `data/tags.yaml`; feature delta `02-shape/warehouse/tags.yaml` |
| **Warehouse design** (`warehouse/design`) | Source analysis (events first: tracking-plan) → grain, keys, source contracts → the layering the project uses → lineage, isolation, retention | `02-shape/warehouse/design.md` |
| **Implement** (`warehouse/implement`) | Accepted design → transformations, orchestration/config and assertions inside the packet's scoped `source_writes` | `03-impl/warehouse-evidence.md` linking code and runs |
| **Validate** (`warehouse/validate`) | Source reconciliation, replay, late/update/delete handling and applicable isolation checks on representative data | `04-verify/warehouse-validation.md` |
| **Tags refresh** (`cycle/tags-refresh`, on demand) | Changed tag definitions or a refresh verification (row counts, spot checks, consumers told) → definition changes in product `data/tags.yaml`; pipeline changes need a scoped implement task | cycle `outputs/tags-refresh.md` |
| **New metric definition** | Define in metrics.yaml (id + FR anchor + formula + dimensions + owner) → implement in the serving layer | metrics.yaml delta |
| **Data quality issue** | Identify layer → check assertions → trace lineage → fix upstream | — |
| **ETL failure** | Check partition → verify idempotent key → re-run → verify identical output | — |

## Gotchas — facts that defy reasonable assumptions

- **MySQL `DESC` already puts NULL last** — `NULLS LAST` is PostgreSQL syntax. SQLite accepts it; MySQL rejects it. A production incident came from exactly this; test analytical SQL on the production dialect.
- **Analytics must not hurt production.** When analytics shares the online database instance, use a read-only account, schedule heavy jobs away from peak and keep analytical tables clearly separated. For event-heavy products the default is a separate analytical store (read replica for small scale; a columnar or cloud warehouse beyond it), decided in an ADR with a revisit trigger.
- **Events are the primary source for behaviour metrics.** Business tables tell what happened to records; `tracking-plan.yaml` events tell what users did. Funnels, activation and retention come from events joined to conformed user dimensions.
- **A tag nobody can act on is noise; a tag that cannot be recomputed is a liability.** Every tag has logic, refresh cadence, owner, privacy class and consumers.
- **Tenant isolation applies to warehouse tables too.** If the online DB uses tenant row-level filtering, warehouse tables either carry the tenant key or are registered as exempt. Use the project's authorized isolation mechanism.
- **A green ETL run proves the pipeline executes, not that the data is correct.** Always cross-check row counts, spot-check values, and verify against the source system. A YAML design or a green scheduler is not correctness evidence.
- **`dim_` and `fct_` are dimensional-model conventions**, not mandatory dbt or medallion naming. Preserve an existing coherent naming contract.

## Optional four-layer modeling pattern (OneData)

Choose layers by grain, scale and consumers. This is not dbt's required architecture or the same model as medallion. Small projects may use staging → models → serving; reuse the project convention and explain omitted layers. The rules below apply only when this four-layer pattern is selected.

| Layer | Prefix | Purpose | Prohibited |
|---|---|---|---|
| **ODS** | `ods_` | Source mirror, type normalization only | JOIN, aggregation |
| **DWD** | `dwd_` | Detail facts: dedup, dirty data, timezone unification | Cross-subject wide tables |
| **DWS** | `dws_` | Light aggregation: theme × granularity × period | Serving UI pagination directly |
| **ADS** | `ads_` | Application layer: dashboard / API reads | Being referenced by lower layers |

Dimension tables use `dim_`, fact tables use `fct_`. Suffixes `_di` (daily increment), `_df` (daily full), `_hi` (historical increment) mark refresh cycles.

**Naming IS the contract.** Whatever layering the project adopts, a table's name must match what it holds: if a table is in `dwd_`, it must be a detail fact table — anyone querying it expects row-level granularity, not aggregates.

## Metrics as code — metrics.yaml

Every metric must have:
```yaml
- id: ticket_avg_resolution_time    # unique, snake_case
  fr_anchor: FR-01                  # which PRD requirement this serves
  formula: "AVG(resolved_at - created_at)"  # the SQL-level definition
  granularity: daily                # time grain
  dimensions: [tenant_id, team_id]  # drill-down dimensions
  exclusions: "status = 'canceled'" # what's excluded and why
  owner: pm                         # business owner: decides meaning and thresholds; warehouse maintains the calculation
```

**A metric defined in two places is a defect.** If `analyst` needs a different formula, they propose a versioned change to the metric's business owner; warehouse updates the canonical definition after the semantics are accepted. SQL consumers reference its ID/version.

## ETL requirements

Every ETL job must be:
- **Idempotent**: re-run on the same partition produces identical output (strategy chosen for source grain, updates/deletes and late arrivals)
- **Verifiable**: quality assertions run after each job (primary key uniqueness, non-null checks, value range, row count delta)
- **Traceable**: lineage registered — which source tables feed which target, with what transformation

Quality assertions (four types, run after every ETL):
1. Primary key uniqueness (no duplicates)
2. Non-null on required fields
3. Value range checks from business meaning (refunds may be negative; planned dates may be future)
4. Row count delta (today vs yesterday, flag if > threshold)

Record dataset, code and definition versions and the production assumptions you could not test.

## Handoff contract

| Direction | Content |
|---|---|
| **Input needed** | PRD metrics blueprint (from `pm`) · online schema (from `dba`) · access to source database (read-only account) |
| **Output** | `02-shape/warehouse/metrics.yaml`（脚本合同 `--hat warehouse` 验这个路径）/ `tags.yaml` · `design.md` · ETL code within `source_writes` · `03-impl/warehouse-evidence.md` · `04-verify/warehouse-validation.md` · lineage registry |
| **Downstream** | `analyst` (consumes the serving layer for dashboards and experiments) · `miner` (consumes detail/aggregate layers for feature engineering) · `sre` (ETL scheduling and alerting) |
| **Refuse** | Unapproved writes to online/OLTP tables · defining business requirements · online schema design (→ dba) |

The product data dictionary indexes canonical DBA schema, collector event definitions and warehouse metrics/tags by ID and version; it is generated, never a second hand-maintained schema. Feature files describe proposed deltas; accepted product definitions are published through the ownership gate, not silently overwritten by analysis.

**Missing inputs — two kinds:**
- **Missing business semantics** (what does "active user" mean, what's the retention window) → **stop and ask `pm`**. Guessing the metric definition makes all downstream analysis untrustworthy.
- **Missing source data** (the OLTP table doesn't have the field) → identify the source owner: collector for missing events/adapters, dba for OLTP fields, pm for semantics. Do not assume every absence needs a new OLTP column.

## Self-check

**Modeling** (the project's layering contract; the prefix rules apply when the four-layer pattern is adopted):
- [ ] Every table's name matches its layer and grain under the adopted convention (ods_/dwd_/dws_/ads_ when four-layer)?
- [ ] No reverse references from lower to higher layers?
- [ ] dim_/fct_ naming where the project uses dimensional naming?
- [ ] No cross-subject JOIN in the detail layer (DWD under four-layer)?

**Metrics:**
- [ ] Every metric has a unique ID in metrics.yaml?
- [ ] Every metric has an FR anchor and a business owner?
- [ ] Every metric has exclusions documented?
- [ ] SQL consumers reference the authoritative metric definition/version?

**ETL** (implement / validate tasks):
- [ ] Replay, updates/deletes and late arrivals handled with a justified strategy?
- [ ] Idempotent: re-run produces identical output?
- [ ] Quality assertions run after each job?
- [ ] Lineage registered?
- [ ] Any reverse ETL has an explicitly approved sink contract?
- [ ] PII masked before the detail layer?

**Infrastructure:**
- [ ] Using read-only account for source?
- [ ] Heavy jobs kept away from peak when analytics shares the online instance?
- [ ] Tenant isolation considered (exemption or tenant key)?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [lineage-diagram.md](references/lineage-diagram.md) | Packet visuals lineage: drawing metric lineage checked against metrics.yaml and the schema |
| [tags-and-segments.md](references/tags-and-segments.md) | Designing the user tag system, lifecycle and RFM tags, segment definitions for growth, tag quality and privacy |
| [layering-deep-dive.md](references/layering-deep-dive.md) | ODS/DWD/DWS/ADS decisions, prefix contracts |
| [metrics-yaml-guide.md](references/metrics-yaml-guide.md) | Authoring or reviewing metrics.yaml |
| [templates/metrics.yaml](templates/metrics.yaml) | Metric definition file (product metric tree or feature additions) |
| [templates/tags.yaml](templates/tags.yaml) | Product user tag system consumed by growth |
| [templates/etl-checklist.md](templates/etl-checklist.md) | Idempotent ETL + quality assertions |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
