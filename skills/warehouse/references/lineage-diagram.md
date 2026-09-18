# Lineage diagrams (data-warehouse-engineer)

Draw one when the packet lists `visuals: [lineage]` (new metrics or datasets). `metrics.yaml` stays the source of truth for metric definitions; the diagram shows where each metric's data comes from.

## How

1. Conventions: `PLUGIN_ROOT/vendor/svg-diagram/SKILL.md`.
2. File: `02-shape/assets/<feature>-lineage.svg`. Right after `<svg …>`:
   `<metadata id="sdlc">{"type": "lineage", "owner": "data-warehouse-engineer", "sources": ["02-shape/warehouse/metrics.yaml", "02-shape/schema.dbml"]}</metadata>`
3. Ids — every id must appear in a declared source:
   - source tables: the table name from the schema
   - datasets / layers (ods, dwd, dws, ads): the dataset name as `metrics.yaml` or the ETL checklist names it
   - metrics: the metric id from `metrics.yaml`
4. Label each edge with the job that moves the data and its schedule; note grain changes (per order → per day).
5. Check and look:
   ```
   python3 PLUGIN_ROOT/scripts/diagram/lint.py --root <feature_dir> <feature_dir>/02-shape/assets/<name>.svg
   bash PLUGIN_ROOT/scripts/diagram/render.sh <feature_dir>/02-shape/assets/shots <feature_dir>/02-shape/assets/<name>.svg
   ```

## What the gate checks

- Every drawn id exists in the declared sources; svg-lint zero errors and zero warnings; digests go stale when `metrics.yaml` or the schema changes.

## Review

A metric whose lineage cannot be drawn from existing sources is a missing source, not a drawing problem: raise it as an open question to the owner.
