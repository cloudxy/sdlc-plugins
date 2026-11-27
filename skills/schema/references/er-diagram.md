# ER and state diagrams (dba)

Draw one when the packet lists `visuals: [er]` (tables or relationships added or changed) or `[state]` (a status field with legal transitions). The DBML stays the source of truth; the diagram is a view of it and is checked against it.

## How

1. Read the drawing conventions: `PLUGIN_ROOT/vendor/svg-diagram/SKILL.md` (layout, spacing, palette, fonts, escaping).
2. Write `02-shape/assets/<feature>-er.svg` (product layer: `<product_root>/assets/erd.svg`). Right after `<svg …>`:
   `<metadata id="sdlc">{"type": "er", "owner": "dba", "sources": ["02-shape/schema.dbml"]}</metadata>`
3. Mark what the picture claims:
   - each table box: `data-sdlc-id="<table>"` (e.g. `orders`)
   - each relationship line: `data-sdlc-id="<table>.<column>-><table>.<column>"` (e.g. `orders.user_id->users.id`); direction and arrow style do not matter
4. Cardinality as text next to the line end: `1`, `0..1`, `0..*`. Do not force crow's feet into the arrow conventions.
5. A logical relationship without a physical foreign key: keep it in DBML with a note (`// logical, no FK`) and draw it dashed. Never draw a constraint the database does not have.
6. Check, then render and look at it:
   ```
   python3 PLUGIN_ROOT/scripts/diagram/lint.py --root <feature_dir> <feature_dir>/02-shape/assets/<feature>-er.svg
   bash PLUGIN_ROOT/scripts/diagram/render.sh <feature_dir>/02-shape/assets/shots <feature_dir>/02-shape/assets/<feature>-er.svg
   ```
   Read the PNG: no clipped names, no lines through boxes, readable at 1280 px. Split by domain when it is not.

## What the gate checks

- Every table and every relationship in the DBML source is drawn, and nothing is drawn that the DBML lacks (DIAGRAM-SEMANTIC).
- svg-lint: zero errors **and zero warnings**.
- Evidence `evidence/diagrams/<name>.json` holds the digests of the SVG and the DBML. Change the DBML later and the diagram is stale: redraw and re-check.

## State diagrams

`"type": "state"`, sources = `02-shape/db-spec.md` (the transition table). Each state `data-sdlc-id="<STATE>"`, each transition `data-sdlc-id="<FROM>-><TO>"`. Every drawn state must appear in the source. The transition list goes to qa for state-coverage tests.

## Mistakes the gate will not catch — review them

- A table drawn at the wrong grain (one row = ?). The grain is stated in db-spec; say it in the box subtitle.
- Money without currency or a snapshot column; time without timezone.
- A giant all-domain ER. Split by bounded context and keep ids stable across the pieces.
