# Stage orchestration

Task contracts and ranks: [stage-map.md](stage-map.md), generated from `workflow/registry.json`. This file owns scheduling and participation guidance.

## Order inside a stage

A stage is a view of participating tasks, not a global lock. Use [work-scope.md](../protocol/work-scope.md) for explicit local targets. Requirements are detailed per imminent slice; exploratory prototypes and high-level architecture/data feasibility may inform them before approved handoff design. API and schema owners reconcile their contracts before dependent implementation. Select external-source, OLTP, telemetry and warehouse work independently. An external-data product should establish source availability and freshness before promising dependent behavior.


- **Discovery:** select research from unresolved questions per discover; reuse accepted evidence and decisions → assumption checks → freeze.
- **Define & Shift-Left triggers (conditional):**
  - **Early technical feasibility (`architect` `define/feasibility`):** dispatch before PM freezes a choice whenever an unproven latency, cost, external source, sync/offline or model/system assumption could change scope or UX. Pass the open question and baseline evidence, not a fictional completed spec; inconclusive results keep dependent choices open.
  - **Early testability & eval oracle (`qa` `define/test-plan`):** invite during define when material acceptance risks exist — `ai-agentic` probabilistic golden-set thresholds, `fintech-ledger` fund/refund invariants, `multi-tenant` isolation, or complex state/concurrency matrices.
  - **Early causal & metric design (`analyst` `define/measurement-plan`):** invite during define when a discovery `bet`, causal A/B or holdout experiment, paired counter-guardrail redline, or probabilistic baseline requires pre-registered measurement before build.
- **Shape (v4):** designer chooses reuse/local-exploration/new-direction scope per design-contract → resolve only pending direction choices → designer `specify` → architect `shape/contract` → dba; invited data-collector follows its domain/event inputs, and data-warehouse-engineer follows the event/source contracts it consumes. **Irreversible & client-release rollback shift-left:** when Q4 (irreversible) or `client-iot-localfirst` / public `api` / `sdk` applies, `shape/contract` and `dba` must design N-2 client/server coexistence, expand-contract migration, feature kill-switches and store-review/distribution rollback paths *before* implementation (never deferred to `deliver`). Parallelize only tasks with disjoint writes and no output dependency. One G-fresh after all of them return.
- **Algorithm & AI task routing (`algo`):** select concrete `algo` tasks by uncertainty and lifecycle rather than treating prompts/models/ranking as generic backend CRUD:
  - `explore`: offline candidate/prompt/model/feature comparison or feasibility spike against explicit constraints before committing production contracts.
  - `evaluate`: run repeatable golden-set, safety/injection refusal, latency and token/inference-COGS benchmarks before claiming quality or passing verify/accept.
  - `diagnose`: isolate badcases, distribution drift, retrieval/citation gaps or metric regressions with reproducible slices before changing weights/prompts/rules.
  - `fix`: implement scoped model/prompt/ranking/rule repair paired with regression evaluation on both target slice and counter-guardrails.
- **Evidence-backed pushback:** when any specialist (`architect`, `qa`, `algo`, `dba`, `pm`, `designer`) returns concrete evidence (code, benchmark, cost math, schema invariant, regulatory rule) showing an upstream requirement, constraint or threshold is unsound or contradictory, **do not force compliance and do not increment `rework_rounds`**. Route business/strategic trade-offs to the operator (Step 4) or mark the flawed upstream artifact `stale` for its owner to revise.
- **Security and privacy review (conditional):** dispatch architect `shape/security-review` only when `q_security: yes`, or when the change touches authentication, session or token lifecycle, tenant or role enforcement, PII minimization, retention or consent, or a new external dependency or vendor lock. Pass the observed surface and the existing authoritative security model, or an explicit note that none exists. The task writes `02-shape/security-review.md` as a delta only and is `partial_stage`: the shape gate still requires `contract.md` and does not require this file. Do not select it for static copy, internal styling, or any change with none of those surfaces. Do not set `q_security` only to schedule it. `q_security` remains Q2/Q3/Q4 and still enforces the contract trust-boundary diagram on its own. Do not widen tests beyond the affected surface. Procedure: [architecture lifecycle](../../../architecture/references/lifecycle.md) and [threat-model.md](../../../architecture/references/threat-model.md).
- **Implement:** per journey slice, name one `slice_integrator` in the ticket and its implementation packets; enforce **contract-first discipline** — lock the git-committed machine-readable contract (`OpenAPI / JSON Schema / Protobuf`, checked via `extra_gates: [contract]`) and publish generated types/mocks first so `frontend` and `backend` build in parallel without drift; the named integrator owns closure with an integration run (`T-n-integration.md`). One G-fresh after the last slice.
- **Architecture change backflow (conditional):** when any producer reports an architecture mismatch, dispatch `shape/change-impact` with the current contracts and evidence. Use its task check, not the aggregate shape gate. Follow [architecture lifecycle](../../../architecture/references/lifecycle.md) for authority, invalidation and revalidation. The manager owns state updates and schedules affected owners; a pending impact report does not authorize changing GWT or resuming dependent work.
- **Impact of a change (read-only):** before marking downstream work stale or scoping a change-impact, run `python3 <PLUGIN_ROOT>/scripts/workflow.py trace <id> --feature <feature_dir>` (or `--project-root <root>` for `metric:`/`tag:`/`event:`/`SIG-` ids) to list the id's definitions, consumers, verification records and gaps. It rebuilds its index from the artifacts and changes nothing; artifact-level stale marking stays the rule where references are incomplete, and each owner re-verifies through its own task.
- **Verify, Release QC & Process QA (`QA 过程监督 ≠ QC 产物检验`):** distinguish **Process QA** (`qa` + upstream seam exit gates `define/test-plan`, `extra_gates: [contract]`, non-orphan GWT/NFR traceability that prevent cross-station defects from being manufactured) from **Product QC** (`reviewer` G-fresh and `qc` release inspection on finished artifacts). During `verify`, QA runs assigned risk/invariant tests; when the contract introduces consequential architecture/security obligations or evidence indicates drift, also dispatch architect `verify/conformance` on the actual build and check records. Required deviations/unverified obligations go to rework or authorized exception plus independent review before verify completes. On escaped-defect closure (`escape:` in `state.yaml`, gated by `ESCAPEQA` at `phase: Closed`), pair Product QC fix verification with Process QA `seam_fix` + `verified_by`.
- **Accept:** revalidate every impacted prior pass as well as failures; pin the current build/design/behavior evidence. pm ∥ designer (ui: yes) ∥ growth (unless skipped). No G-fresh here; the final review reads the acceptance files.
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
| shape (architect security-review) | Observed auth/privacy/supply-chain surface, plus the existing authoritative security model or an explicit note that none exists. Accepted spec or contract only when they already exist |
| shape (architect change-impact) | Current accepted spec/contract versions, observed mismatch and reproduction evidence, affected consumer list |
| verify (architect conformance) | Accepted architecture/security obligations, actual code/build revision and raw verification records |
| dba | spec, `02-shape/contract.md` |
| collect/tracking | event requirements (`tracking.md` when defined there), collection contract |
| collect/source | product data need, source constraints/access and freshness questions; no telemetry requirement |
| warehouse/design | accepted data need and source contracts; no mandatory tag/metric subsystem |
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
| `q_security: yes`, or auth/session/tenant, PII retention/consent, or a new external dependency or vendor lock | architect `shape/security-review` | not selected when none of those surfaces change |
| Q1 schema = yes (L2+) | dba | never skipped when the schema changes |
| user-facing change (L2+) | growth: affected claims check; positioning only when changed | `roles_skipped: [growth]` + reason (internal tool, pure refactor) |
| `tracking: yes` | pm writes `tracking.md`; data-collector at L3+ or when identity/pipeline changes | `tracking: no` + `埋点：N/A（理由）` in the spec |
| L3 | qc, sre, ops enablement, growth launch | `roles_skipped` + reason |
| L4 | data-collector, data-warehouse-engineer, analyst | `roles_skipped` + reason |

## Architecture task closure

Architecture methods and output completeness have one source: [architecture lifecycle](../../../architecture/references/lifecycle.md). Before dispatch, expand its applicable artifact inventory into the packet's deliverable paths and actual input files (not whole directories). After return, check every declared output and the task's professional criteria. New outputs discovered during work require a revised packet. `check-task` validates only registry minimum presence; it does not certify technical quality, accepted decisions or runtime evidence.

Optional architecture tasks do not add a new mandatory lane stage. `shape/security-review` is one of them: select it only for the auth, privacy and supply-chain surfaces above. They must still be tracked as participating tasks when selected; keep the parent stage open until their applicable decisions/evidence are resolved. A lifecycle report may be complete while its dependent work remains blocked. Update product facts only under the architect's authorized write scope and lifecycle evidence rules; otherwise return the proposed delta for a product/bootstrap refresh.

## Conditional task chain beyond artifact design

- Use [industry-playbooks.md](../routing/industry-playbooks.md) to map `project_profile` (`industry` + `traits`) to the four domain SOP references and shift-left triggers above. Partial define tasks (`define/feasibility`, `define/test-plan`, `define/measurement-plan`) must never demand finished build evidence.
- For AI/ML/ranking/rule-scoring surfaces (`ai-agentic`, `aigc-workbench`, `ai-enabled` trait, search/recommendation), schedule `algo` (`explore`, `evaluate`, `diagnose`, `fix`) alongside or ahead of `backend` integration so probabilistic thresholds and token/latency guardrails are measured, not asserted.
- After collector design/source acceptance, schedule `collect/implement` then `collect/validate` when collection code changes. After warehouse definitions/design acceptance, schedule `warehouse/implement` then `warehouse/validate` when pipelines change. Include results in verify; design-only tasks cannot establish data delivery.
- Use DBA `migration` for changed database evolution and `optimize` for query work; primary schema skill decides applicable proof. Use SRE `ci` when project pipeline wiring changes. Their partial task checks do not force all deliver/shape artifacts prematurely.
- Use designer `market/prototype` for a question-driven scratch experiment, including unresolved requirements before specification approval. Final product design prototypes stay under design-contract and do not satisfy production implementation evidence.
- Cycle tasks (`stage: cycle`) run only inside a product cycle (`/sdlc-product cycle <id>`, [product-mode.md](product-mode.md) § Cycle mode); a feature lane never dispatches them. A feature's define reads the cycle's decisions and cites signal ids as inputs.
- Record selected tasks, prerequisites, outputs, status and unresolved obligations in manager state. Ranks are stage vocabulary, not a prohibition on early partial tasks. A report's existence never closes another task's dependency.

## Protocol-1 pilot inputs

For pm/define/spec, architect/verify/conformance and backend/implement/T-n, use the generated [task-inputs.md](../protocol/task-inputs.md) and [task-protocol.md](../protocol/task-protocol.md). These override prose shortcuts for those exact tasks. Early feasibility, test-plan and explore keep their own contracts; this table remains the scheduling authority for unencoded participation choices.


## Short-path eligibility

**L2-short predicate (closed set) — skips only the architect:** (a) `intent.skip_shape: true` and `02-shape/contract.md` already on disk; or (b) the implement packet marks the contract `required: false` and names `spec.md` as its substitute. `path: short` or appetite < 4h alone is not enough.
