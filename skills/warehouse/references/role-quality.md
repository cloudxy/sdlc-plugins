# Data Warehouse Engineer Excellence & Review Rubric

Apply alongside [warehouse SKILL.md](../SKILL.md) across `data/metrics.yaml`, `data/tags.yaml`, `02-shape/warehouse/*`, `03-impl/warehouse-evidence.md`, `04-verify/warehouse-validation.md` and `04-verify/data-audit.md`.

## 1. Task-Specific Quality Bar

| Task | Excellence Bar | Reject (`major` / `blocker`) |
|---|---|---|
| `metrics` & `tags` (`metrics.yaml` · `tags.yaml`) | SVOT files carry top-level `version`, per-item `effective_from`, `time_semantics`, `exclusions`, `owner`, and coherent `privacy` vs `consumers` | Duplicate ad-hoc SQL definitions, silent unversioned formula edits, or `internal`/`sensitive` tags wired to `growth` outreach |
| `design` & `implement` | Right-sized layering (`staging→marts` or `ODS/DWD/DWS/ADS`), explicit atomic grain, idempotent partition/merge strategy, production SQL dialect | Forcing 4 layers onto trivial scopes, lower layers querying `ads_`, direct OLTP writes, or SQLite-only dialect checks (`NULLS LAST`) |
| `validate` / `audit` / `backfill` (`warehouse-validation.md`) | Pinned snapshot reconciliation against source counts/sums, two-run `0`-diff idempotency proof, late-arrival/delete/refund checks | Treating a green scheduler exit code or YAML file as data-correctness proof |

## 2. SVOT Semantic & Privacy Governance

- **Single Version of Truth (SVOT)**: Operational DBs/logs hold raw facts (SSOT); `metrics.yaml` and `tags.yaml` govern versioned analytical meaning (`metric:<id>@v<n>`, `tag:<id>@v<n>`). Every definition specifies `time_semantics` (`event_time` / `business_time` / `ingestion_time` + late-arrival cutoff) and `effective_from`.
- **Outreach privacy & point-in-time safety**: Tags consumed by `growth` for user targeting use `public` or `operational` privacy classes (`internal` is restricted to internal analytics or exclusion filters; `sensitive` is barred from marketing). Model tags attach a model card and enforce point-in-time feature windows with zero future leakage.

## 3. Idempotent Replay, Domain Economics & Isolation

- **Replay & CDC delete correctness**: Pipelines produce byte-identical partitions across re-runs (`run1` vs `run2` diff = empty) and handle late arrivals, updates and CDC hard-delete tombstones without row multiplication or ghost records.
- **Domain-aware sign & conservation assertions**: Never block valid negative refunds, chargebacks or reversals with naive `amount >= 0` checks; assert sign rules by transaction type and reconcile net conservation (`gross + refund == net`) against upstream sources.
- **OLTP & tenant protection**: Query OLTP strictly through read-only accounts/replicas off-peak; mask/tokenize PII before detail/serving layers; enforce `tenant_id` row isolation or an explicitly authorized system-context exemption.
