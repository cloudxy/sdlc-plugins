# Business flow and state diagrams (pm)

Draw one when the packet lists `visuals: [flow]` (a journey with three or more branches) or `[state]` (a new business state machine). The spec stays the source of truth; the diagram helps design, architecture and qa read the branches the same way.

## How

1. Conventions: `PLUGIN_ROOT/vendor/svg-diagram/SKILL.md`.
2. File: `01-define/assets/<journey>-flow.svg`. Right after `<svg …>`:
   `<metadata id="sdlc">{"type": "flow", "owner": "pm", "sources": ["01-define/spec.md"]}</metadata>`
3. Ids:
   - the journey or requirement each part shows: `data-sdlc-id="J-2"`, `data-sdlc-id="FR-7"` — at least one is required, and each must exist in the spec
   - decision points and end states: the rule or state name as the spec writes it
4. Show the trigger, every decision, every end state, and the error and cancel paths — the branches are the reason to draw.
5. Check and look:
   ```
   python3 PLUGIN_ROOT/scripts/diagram/lint.py --root <feature_dir> <feature_dir>/01-define/assets/<name>.svg
   bash PLUGIN_ROOT/scripts/diagram/render.sh <feature_dir>/01-define/assets/shots <feature_dir>/01-define/assets/<name>.svg
   ```

## What the gate checks

- The flow names J-n / FR-n ids, and every id and label drawn exists in the spec.
- svg-lint zero errors and zero warnings; the evidence goes stale when the spec changes.

## Not a wireframe

Screens, layout and copy belong to the designer's prototypes. A flow shows steps and decisions, not pages.
