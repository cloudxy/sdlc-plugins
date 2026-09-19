# Architecture, sequence and trust-boundary diagrams (architect)

Draw them when the packet lists them in `visuals`. For `shape/contract`, `trust-boundary` is required whenever `q_security: yes` (the packet check enforces it); early feasibility and conformance do not require a new final-design diagram; `architecture` and `sequence` when calls between services or modules change. `contract.md`, referenced ADRs and the product baseline remain the respective canonical sources; a diagram is a view. Product diagrams cite `architecture.md` and distinguish implemented/deployed facts from planned deltas.

## How

1. Conventions: `PLUGIN_ROOT/vendor/svg-diagram/SKILL.md`.
2. File: `02-shape/assets/<feature>-<type>.svg` (product layer: `<product_root>/assets/architecture.svg`). Right after `<svg …>`:
   `<metadata id="sdlc">{"type": "architecture", "owner": "architect", "sources": ["02-shape/contract.md"]}</metadata>`
3. Ids — every id must appear in a source, so name things as `contract.md` names them:
   - components / services / stores: `data-sdlc-id="<component name as in contract.md>"`
   - sequence steps: the participants' names; mark the call with the endpoint or event name used in the contract
   - trust boundaries: `data-sdlc-id="<SEC-n>"` for each control from the contract's `[SEC-n]` list, placed where it is enforced
4. Proposed vs existing: draw what exists solid and what this change adds or moves in the change colour, with a legend outside the drawing area. A deployment view names its environment.
5. Check and look:
   ```
   python3 PLUGIN_ROOT/scripts/diagram/lint.py --root <feature_dir> <feature_dir>/02-shape/assets/<name>.svg
   bash PLUGIN_ROOT/scripts/diagram/render.sh <feature_dir>/02-shape/assets/shots <feature_dir>/02-shape/assets/<name>.svg
   ```

## What the gate checks

- Every drawn id appears in `contract.md` (or the other declared sources): no component exists only in the picture.
- svg-lint zero errors and zero warnings; evidence digests go stale when `contract.md` changes.

## Mistakes to review

- A directory tree drawn as "architecture". Show runtime units and who calls whom, with protocols.
- Arrows without direction meaning (data flow vs dependency vs call). Say which in the legend.
- A trust boundary with no control on it: every `[SEC-n]` on the diagram links to a test or check in the contract.
