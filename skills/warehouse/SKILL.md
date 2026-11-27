---
name: "warehouse"
description: "Use this skill when the spawn packet names data-warehouse-engineer or $warehouse. Do NOT load in /sdlc or for OLTP schema."
when_to_use: "Use this skill when the spawn packet names hat data-warehouse-engineer or the user types $warehouse / names this hat. Do NOT use from parent /sdlc. Do NOT use for OLTP schema or experiment design."
---

# Warehouse — SVOT metric tree, user tags, layered models, idempotent ETL

Job: **build the analytical data foundation the product runs on** — a **Single Version of Truth (SVOT)** per metric and user tag (`<product_root>/data/metrics.yaml`, `<product_root>/data/tags.yaml`), versioned with explicit time semantics, and idempotent pipelines reconciled against source systems.

Select warehouse work only when analytical/serving needs justify it. A collection-only product does not automatically need metrics, user tags or a multi-layer warehouse.

Three values guide everything:

1. **SVOT — Metrics & tags as versioned code.** Operational stores (`schema` / `collect`) are the **SSOT** for raw facts; `data/metrics.yaml` and `data/tags.yaml` are the **SVOT (Single Version of Truth)** for analytical meaning. Every metric and tag carries a canonical `id`, file `version`, `effective_from`, and `time_semantics` (`event_time` / `business_time` / `ingestion_time`). Dashboards, growth segments, experiments and `retro` readouts cite `metric:<id>@v<n>` / `tag:<id>@v<n>`; independently redefining formulas in ad-hoc SQL or breaking semantics without bumping version + `effective_from` is a defect.
2. **Idempotent, replay-safe ETL.** Every pipeline produces identical results when re-run on the same input window. Choose partition overwrite, key-based merge/upsert (handling CDC updates + delete tombstones), or immutable append + deterministic dedup from source semantics ([industry-data-sops.md](../schema/references/industry-data-sops.md)).
3. **Data flows one way.** OLTP/events → warehouse → serving/analysis. Reverse ETL requires a separate, explicitly approved sink contract with rate, idempotency, privacy and ownership controls; analytical jobs never mutate OLTP tables directly.

| Task | Approach | Output |
|---|---|---|
| **Product metric tree** (`warehouse/metrics`) | North star (named by `pm` in `strategy.md`) → drivers → guardrails with red lines, `version`, `effective_from`, `time_semantics` ([templates/metrics.yaml](templates/metrics.yaml)) | product `data/metrics.yaml`; feature delta `02-shape/warehouse/metrics.yaml` |
| **User tag system** (`warehouse/tags`) | Fact, rule and model tags computable from `tracking-plan.yaml` events and business tables ([templates/tags.yaml](templates/tags.yaml), [tags-and-segments.md](references/tags-and-segments.md)). Outreach tags use `public` / `operational` privacy, never `internal`/`sensitive` | product `data/tags.yaml`; feature delta `02-shape/warehouse/tags.yaml` |
| **Warehouse design** (`warehouse/design`) | Source contracts → grain, keys, `time_semantics`, late-arrival/delete rules → project layering → lineage, tenant isolation, retention | `02-shape/warehouse/design.md` |
| **Implement** (`warehouse/implement`) | Accepted design → transformations, orchestration and quality assertions ([templates/etl-checklist.md](templates/etl-checklist.md)) inside scoped `source_writes` | `03-impl/warehouse-evidence.md` |
| **Validate** (`warehouse/validate`) | Source reconciliation, double-run idempotency diff, late/update/delete handling, negative refund/reversal conservation and isolation checks ([templates/warehouse-validation.md](templates/warehouse-validation.md)) | `04-verify/warehouse-validation.md` |
| **Audit** (`warehouse/audit`) | Question + pinned dataset + quality rules; investigate affected partitions, lineage and discrepancy without silently mutating production | `04-verify/data-audit.md` |
| **Backfill** (`warehouse/backfill`) | Accepted recovery plan + pinned dataset; isolate staging output, protect concurrent increments, prove idempotency and reconcile counts/sums | `03-impl/backfill-evidence.md` |
| **Tags refresh** (`cycle/tags-refresh`) | Updated tag definitions or refresh verification (coverage, drift, spot checks, consumer notice) | cycle `outputs/tags-refresh.md` |

## Gotchas — facts that defy reasonable assumptions

Long operations use the manager's [continuous-work job protocol](../sdlc/references/modes/continuous-work.md): return job identity and checkpoints; submission proves launch, while completion requires terminal success plus reconciliation. Schema expansion coexists with old consumers; contraction waits until old consumers exit.

- **MySQL `DESC` already puts NULL last** — `NULLS LAST` is PostgreSQL syntax. SQLite accepts it; MySQL rejects it. Test analytical SQL on the production dialect.
- **Analytics must not hurt production.** On a shared instance, use a read-only account, off-peak scheduling and isolated table prefixes; for event-heavy workloads use a read replica or columnar/OLAP store decided via ADR.
- **Time semantics drift silently breaks month-end numbers.** Always declare whether a metric/fact partitions by `event_time` (user action), `business_time` (order paid / settled / refunded), or `ingestion_time` (arrival), plus the late-arrival lookback window.
- **Refunds, reversals and chargebacks are legitimately negative.** Never write naive `amount >= 0` assertions that drop or block valid negative adjustments; assert domain-aware sign rules by transaction type and net ledger conservation (`gross - refunds == net`).
- **Tag privacy classes govern outreach.** `internal` ("analytics only, no outreach") and `sensitive` tags cannot be consumed by `growth` campaigns; tags intended for targeting/win-back use `public` or `operational` (outreach-permitted without exposing raw sensitive values).
- **Tenant isolation & PII masking apply to warehouse tables too.** Carry `tenant_id` (or register an authorized system-context exemption) and mask/tokenize PII before detail/serving layers.
- **A green ETL run proves execution, not correctness.** Reconcile row counts and additive sums against source tables, run a two-pass idempotency diff, and verify edge cases in `04-verify/warehouse-validation.md`.

## Optional four-layer modeling pattern (OneData)

Choose layers by grain, scale and consumers ([layering-deep-dive.md](references/layering-deep-dive.md)). Small or dbt-based projects may use `staging → marts/serving`; preserve an existing coherent convention and explain omitted layers. When the four-layer pattern is adopted:

| Layer | Prefix | Purpose | Prohibited |
|---|---|---|---|
| **ODS** | `ods_` | Source mirror, type normalization only | JOIN, aggregation, business filtering |
| **DWD** | `dwd_` | Atomic detail facts: dedup, PII masking, timezone unification | Cross-subject wide tables, aggregation |
| **DWS** | `dws_` | Light summary: theme × grain × period (`_di`/`_df`/`_hi`) | Serving UI pagination directly |
| **ADS** | `ads_` | Serving layer for BI / APIs / tag wide tables | Being referenced by lower layers |

Dimension tables use `dim_`, fact tables use `fct_`. **Naming IS the grain contract.**

## SVOT — Metrics as code (`metrics.yaml`)

```yaml
version: 1
metrics:
  - id: ticket_avg_resolution_time
    fr_anchor: FR-01
    formula: "AVG(TIMESTAMPDIFF(SECOND, created_at, resolved_at))"
    granularity: daily
    time_semantics: business_time     # resolved_at business timestamp (7d late-arrival window)
    effective_from: "2026-09-01"
    dimensions: [tenant_id, team_id]
    exclusions: "status = 'canceled'"
    owner: pm                         # business owner; warehouse maintains calculation
```

## ETL quality assertions & Minimum Viable Data Product 9-Element Contract

Run executable quality assertions after every job (fail-closed before publishing to serving views):
1. **Primary/idempotent key uniqueness** (zero duplicate business keys per grain)
2. **Non-null** on required keys, timestamps and dimensions
3. **Domain-aware value & sign invariants** (e.g. `sale >= 0`, `refund <= 0` linked to parent order, `net == gross + refund`; future dates allowed only on planned fields)
4. **Row-count & sum reconciliation** against upstream source + day-over-day delta & freshness SLA bounds

Every published analytical dataset, `ADS`/mart table, metric view, or tag table must satisfy the **Minimum Viable Data Product 9-Element Contract** (no element omitted at exit):
1. **① Owner (`owner`)**: accountable business owner + maintaining `data-warehouse-engineer`.
2. **② Upstream/downstream data contract**: explicit schema, field & time semantics (`event_time` / `business_time` / `ingestion_time` + `availability_time`), freshness SLA, quality bounds, and security classification.
3. **③ Executable quality assertions**: automated post-run checks (1–4 above) returning `exit: 0` before downstream exposure.
4. **④ Run logs**: persisted execution telemetry (`run_id`, window/partition, source/target row counts, duration, exit status).
5. **⑤ Lineage**: traceable table & metric lineage from raw source (`collect`/`schema`) through layers to serving targets.
6. **⑥ Semantic documentation (`SVOT`)**: canonical versioned definition in `data/metrics.yaml` or `data/tags.yaml` (`metric:<id>@v<n>` / `tag:<id>@v<n>`).
7. **⑦ Explicit consumers**: registered downstream consumers (`analyst`, `growth`, `miner`, `ops`, BI/API endpoints).
8. **⑧ Permission / privacy boundary**: `tenant_id` isolation (or approved system-context exemption), PII masking/tokenization before detail/serving layers, and tag outreach privacy tier (`public`/`operational` vs `internal`/`sensitive`).
9. **⑨ Breaking-change notification mechanism**: version bump + `effective_from` + expand-contract coexistence window + proactive notice to all registered consumers in ⑦ before schema or formula changes.

## Handoff contract

| Direction | Content |
|---|---|
| **Input needed** | PRD metrics blueprint (`pm`) · `data/tracking-plan.yaml` (`data-collector`) · online schema (`dba`) · read-only source access |
| **Output** | `02-shape/warehouse/metrics.yaml` / `tags.yaml` · `02-shape/warehouse/design.md` (with 9-element data product contract) · ETL code within `source_writes` · `03-impl/warehouse-evidence.md` · `04-verify/warehouse-validation.md` ([templates/warehouse-validation.md](templates/warehouse-validation.md)) · lineage |
| **Downstream** | `analyst` (cites `metric:<id>@v<n>`) · `growth` (targets `public`/`operational` tags) · `miner` (consumes `event_time` + `availability_time` features & proposes model tags) · `sre` (scheduling/alerts) |
| **Refuse** | Unapproved OLTP writes · inventing business metric semantics (`→ pm`) · online OLTP schema design (`→ dba`) · publishing uncontracted tables missing any of the 9 data-product elements |

## Self-check

- [ ] Table names match adopted layer and atomic grain, with zero reverse references from lower to higher layers?
- [ ] All **9 elements of the Minimum Viable Data Product Contract** (① owner, ② contract/SLA, ③ executable assertions, ④ run logs, ⑤ lineage, ⑥ SVOT docs, ⑦ explicit consumers, ⑧ permission/privacy boundary, ⑨ breaking-change notification) verified?
- [ ] `metrics.yaml` and `tags.yaml` carry `version`, `effective_from`, `time_semantics`, `exclusions`, `owner`, and coherent `privacy` vs `consumers`?
- [ ] ETL handles replay, late arrivals, updates and CDC delete tombstones idempotently (two-run diff = empty)?
- [ ] Domain-aware assertions allow valid negative refunds/reversals while reconciling net totals to source?
- [ ] PII masked/tokenized before detail/serving layers; read-only source account & tenant isolation verified?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [lineage-diagram.md](references/lineage-diagram.md) | Packet `visuals: [lineage]`: drawing metric lineage checked against `metrics.yaml` and schema |
| [tags-and-segments.md](references/tags-and-segments.md) | Designing fact/rule/model tags, lifecycle/RFM segments, `operational` vs `internal` privacy |
| [layering-deep-dive.md](references/layering-deep-dive.md) | Optional ODS/DWD/DWS/ADS rules, star schema, idempotent partition/merge patterns, tenant isolation |
| [metrics-yaml-guide.md](references/metrics-yaml-guide.md) | Authoring or reviewing SVOT `metrics.yaml` (`version`, `effective_from`, `time_semantics`) |
| [industry-data-sops.md](../schema/references/industry-data-sops.md) | Point-in-time joins (zero data leakage), CDC tombstone merges, financial ledger reconciliation |
| [templates/metrics.yaml](templates/metrics.yaml) | Product SVOT metric tree or feature delta |
| [templates/tags.yaml](templates/tags.yaml) | Product SVOT user tag catalog |
| [templates/etl-checklist.md](templates/etl-checklist.md) | Layer-agnostic idempotent ETL & domain-aware assertion checklist |
| [templates/warehouse-validation.md](templates/warehouse-validation.md) | Reconciliation, replay & isolation validation report (`04-verify/warehouse-validation.md`) |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
