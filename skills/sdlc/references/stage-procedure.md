# Stage orchestration

Task contracts and ranks: [stage-map.md](stage-map.md), generated from `workflow/registry.json`. This file owns scheduling and participation guidance.

## Order inside a stage

- **Discovery:** select research from unresolved questions per discover; reuse accepted evidence and decisions → assumption checks → freeze.
- **Define / early feasibility (conditional):** if an unresolved technical assumption can change scope or experience, dispatch architect `define/feasibility` before PM freezes that choice. Pass the question and available evidence, not a fictional completed spec. Route results to PM/designer; inconclusive results keep dependent choices open. It may also inform design exploration.
- **Shape (v4):** designer chooses reuse/local-exploration/new-direction scope per design-contract → resolve only pending direction choices → designer `specify` → architect `shape/contract` → dba; invited data-collector follows its domain/event inputs, and data-warehouse-engineer follows the event/source contracts it consumes. Parallelize only tasks with disjoint writes and no output dependency. One G-fresh after all of them return.
- **Implement:** per journey slice, name one `slice_integrator` in the ticket and its implementation packets; backend publishes the contract mock first; frontend builds against it in parallel; the named integrator owns closure with an integration run (`T-n-integration.md`). One G-fresh after the last slice.
- **Architecture change backflow (conditional):** when any producer reports an architecture mismatch, dispatch `shape/change-impact` with the current contracts and evidence. Use its task check, not the aggregate shape gate. Follow [architecture lifecycle](../../architecture/references/lifecycle.md) for authority, invalidation and revalidation. The manager owns state updates and schedules affected owners; a pending impact report does not authorize changing GWT or resuming dependent work.
- **Verify:** QA runs its assigned tests. When the contract introduces consequential architecture/security obligations or evidence indicates drift, also dispatch architect `verify/conformance`, consuming the actual build and check records. Schedule it after the evidence it needs. Required deviations/unverified obligations go to rework or authorized exception plus independent review before declaring verify complete; a report file alone is insufficient. Include the report and unresolved obligations in reviewer/QC inputs.
- **Accept:** pm ∥ designer (ui: yes) ∥ growth (unless skipped). No G-fresh here; the final review reads the acceptance files.
- **Release readiness:** SRE `deliver/prepare` precedes QC for release-ready/deployed targets. After QC, authorized SRE execution may proceed; ops/growth can draft documents earlier but publication and campaigns follow actual availability and authorization. G-fresh on the sre checklist only; enablement and launch are G-script.

## Required inputs per stage

| Stage (task) | Required inputs (besides `product_context`) |
|---|---|
| growth (positioning) | `00-discover/compete.md`, `00-discover/market.md`, frame |
| define | `00-discover/briefing.md` (L2+), `01-define/requirement-pool.md` if ops ran |
| designer (explore) | accepted spec; briefing/growth/compete only when relevant to unresolved design decisions |
| designer (specify) | spec, `02-shape/design-directions.md`, the picked direction (`state.design.picked`) |
| define (architect feasibility) | Open technical question, briefing/known constraints, existing baseline/code/evidence; completed spec not required |
| shape (architect contract) | Approved spec, baseline, feasibility results if any; on ui: yes approved final prototype source/version, component IDs, tokens, flows, edge-states and direction decision |
| shape (architect change-impact) | Current accepted spec/contract versions, observed mismatch and reproduction evidence, affected consumer list |
| verify (architect conformance) | Accepted architecture/security obligations, actual code/build revision and raw verification records |
| dba | spec, `02-shape/contract.md` |
| collect | `01-define/tracking.md`, contract |
| implement | ticket, contract, spec (journeys J-n), briefing (the why); on ui: yes the final prototype `02-shape/prototypes/final/` (code, not screenshots), `flows.md`, `edge-states.md`; on tracking: yes `tracking.md` |
| verify | spec, contract/verification plan, all `03-impl/*` evidence and integration files; tracking/state files only when applicable |
| accept (walkthrough) | briefing, spec, `coverage.md`, consumer integration and journey execution evidence (screenshots when UI) |
| accept (design-qa) | `design-directions.md`, `flows.md`, `edge-states.md`, final prototype source/version and runtime screenshots |
| accept (claims-check) | `00-discover/growth.md`, spec, applicable build evidence, any release-note or campaign draft |
| review (final) | all feature artifacts, `product-delta.md`, the product files it lists |
| qc | `findings.md`, `coverage.md`, `accept-*.md`, pasted matrix fingerprint; SRE readiness for release targets; architecture conformance and exception records when applicable |
| deliver · enablement · launch | release opinion; launch also `accept-growth.md` |
| retro | `metrics.yaml`, launch plan, production data access |

## Participation rules

| Condition | Participates | Skip only with |
|---|---|---|
| `ui: yes` (L2+) | designer: scoped exploration/reuse, specify, accept | never skipped on a UI change |
| Q1 schema = yes (L2+) | dba | never skipped when the schema changes |
| user-facing change (L2+) | growth: affected claims check; positioning only when changed | `roles_skipped: [growth]` + reason (internal tool, pure refactor) |
| `tracking: yes` | pm writes `tracking.md`; data-collector at L3+ or when identity/pipeline changes | `tracking: no` + `埋点：N/A（理由）` in the spec |
| L3 | qc, sre, ops enablement, growth launch | `roles_skipped` + reason |
| L4 | data-collector, data-warehouse-engineer, analyst | `roles_skipped` + reason |

## Architecture task closure

Architecture methods and output completeness have one source: [architecture lifecycle](../../architecture/references/lifecycle.md). Before dispatch, expand its applicable artifact inventory into the packet's deliverable paths and actual input files (not whole directories). After return, check every declared output and the task's professional criteria. New outputs discovered during work require a revised packet. `check-task` validates only registry minimum presence; it does not certify technical quality, accepted decisions or runtime evidence.

Optional architecture tasks do not add a new mandatory lane stage. They must still be tracked as participating tasks when selected; keep the parent stage open until their applicable decisions/evidence are resolved. A lifecycle report may be complete while its dependent work remains blocked. Update product facts only under the architect's authorized write scope and lifecycle evidence rules; otherwise return the proposed delta for a product/bootstrap refresh.

## Conditional task chain beyond artifact design

- During define, invite QA `test-plan` for material acceptance/testability risks, and analyst `measurement-plan` when an outcome/experiment requires measurement. These partial tasks must not demand finished execution evidence.
- After collector design/source acceptance, schedule `collect/implement` then `collect/validate` when collection code changes. After warehouse definitions/design acceptance, schedule `warehouse/implement` then `warehouse/validate` when pipelines change. Include results in verify; design-only tasks cannot establish data delivery.
- Use DBA `migration` for changed database evolution and `optimize` for query work; primary schema skill decides applicable proof. Use SRE `ci` when project pipeline wiring changes. Their partial task checks do not force all deliver/shape artifacts prematurely.
- Use designer `market/prototype` only for a question-driven scratch experiment. Final product design prototypes stay under design-contract and do not satisfy production implementation evidence.
- Record selected tasks, prerequisites, outputs, status and unresolved obligations in manager state. Ranks are stage vocabulary, not a prohibition on early partial tasks. A report's existence never closes another task's dependency.
