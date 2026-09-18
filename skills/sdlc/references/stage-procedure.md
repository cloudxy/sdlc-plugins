# Stage orchestration

Task contracts and ranks: [stage-map.md](stage-map.md), generated from `workflow/registry.json`. This file owns scheduling and participation guidance.

## Order inside a stage

- **Discovery:** market ∥ compete → growth (needs the alternatives from compete) → HITL discuss → falsify → freeze.
- **Shape (v4):** designer `explore` → **human picks a direction** → designer `specify` → architect → dba; invited data-collector follows its domain/event inputs, and data-warehouse-engineer follows the event/source contracts it consumes. Parallelize only tasks with disjoint writes and no output dependency. One G-fresh after all of them return.
- **Implement:** per journey slice, name one `slice_integrator` in the ticket and its implementation packets; backend publishes the contract mock first; frontend builds against it in parallel; the named integrator owns closure with an integration run (`T-n-integration.md`). One G-fresh after the last slice.
- **Accept:** pm ∥ designer (ui: yes) ∥ growth (unless skipped). No G-fresh here; the final review reads the acceptance files.
- **Deliver (L3):** after qc — sre ∥ ops enablement ∥ growth launch. G-fresh on the sre checklist only; enablement and launch are G-script.

## Required inputs per stage

| Stage (task) | Required inputs (besides `product_context`) |
|---|---|
| growth (positioning) | `00-discover/compete.md`, `00-discover/market.md`, frame |
| define | `00-discover/briefing.md` (L2+), `01-define/requirement-pool.md` if ops ran |
| designer (explore) | `01-define/spec.md`, briefing, `00-discover/growth.md`, `00-discover/compete.md` |
| designer (specify) | spec, `02-shape/design-directions.md`, the picked direction (`state.design.picked`) |
| shape (architect) | spec; on ui: yes also `design-directions.md` + `flows.md` |
| dba | spec, `02-shape/contract.md` |
| collect | `01-define/tracking.md`, contract |
| implement | ticket, contract, spec (journeys J-n), briefing (the why); on ui: yes the final prototype `02-shape/prototypes/final/` (code, not screenshots), `flows.md`, `edge-states.md`; on tracking: yes `tracking.md` |
| verify | spec, `tracking.md`, all `03-impl/*` evidence and integration files, `edge-states.md` |
| accept (walkthrough) | briefing, spec, `coverage.md`, integration and E2E screenshots |
| accept (design-qa) | `design-directions.md`, `flows.md`, `edge-states.md`, screenshots |
| accept (claims-check) | `00-discover/growth.md`, spec, screenshots, any release-note or campaign draft |
| review (final) | all feature artifacts, `product-delta.md`, the product files it lists |
| qc | `findings.md`, `coverage.md`, `accept-*.md`, pasted matrix fingerprint |
| deliver · enablement · launch | release opinion; launch also `accept-growth.md` |
| retro | `metrics.yaml`, launch plan, production data access |

## Participation rules

| Condition | Participates | Skip only with |
|---|---|---|
| `ui: yes` (L2+) | designer: explore, specify, accept | never skipped on a UI change |
| Q1 schema = yes (L2+) | dba | never skipped when the schema changes |
| user-facing change (L2+) | growth: positioning, accept | `roles_skipped: [growth]` + reason (internal tool, pure refactor) |
| `tracking: yes` | pm writes `tracking.md`; data-collector at L3+ or when identity/pipeline changes | `tracking: no` + `埋点：N/A（理由）` in the spec |
| L3 | qc, sre, ops enablement, growth launch | `roles_skipped` + reason |
| L4 | data-collector, data-warehouse-engineer, analyst | `roles_skipped` + reason |
