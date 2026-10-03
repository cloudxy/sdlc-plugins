# Scoped work: delivery, refinement and defect repair

Read at entry when the user names a stopping point, revisits an existing artifact, or reports a defect. All entries use the same registered tasks, task graph, ownership and evidence protocol. `single-hat` remains the small one-producer shortcut; product/cycle keep their own scopes.

The shortcut still uses a WorkItem when it needs durable completion/resume; only temporary read-only advice may remain a chat answer. For version coexistence, cross-feature dependencies, coordinated state updates or isolated concurrent writers, use [continuous-work.md](continuous-work.md). Multiple active work items are valid; `active_work` selects a resume target, not an exclusive project phase.

## Resolve the request before resuming

Explicit current scope wins over an unfinished feature. Identify the feature/object, the requested improvement, accepted input versions, observable completion criteria and whether to continue. Reuse recorded decisions; ask only for missing consequential choices. A bare “continue” resumes `active_work` if present, otherwise the feature's unfinished tasks. Completed scoped work is not an implicit request to start implementation.

- **create:** select the tasks needed for the requested outcome, including a proposal-only handoff.
- **refine:** compare feedback with the current baseline; select affected producers and appropriate reviewers. A request such as “补齐退款权限和异常规则，停在需求确认” may need PM, early QA and a feasibility question; it is not necessarily one role.
- **fix:** bind the defect, expected behavior, reproduction and source/release baseline. Locate the mechanism, repair, independently verify and accept affected behavior. For a shipped/closed feature, create a linked change directory and preserve its historical records. An active feature can keep the defect work in its graph.

`mode: refine` / `/sdlc-refine` and `mode: fix` / `/sdlc-fix` are entry shortcuts. They do not create separate engines or grant production authority. Natural-language requests route identically. “Diagnose only” stops with diagnosis; “fix and verify” includes repair and verification.

## Scope, target and risk

Keep the feature's `delivery_goal` and lane. A local work item has a concrete textual `target` and selected completion levels; completing it claims only that scope. Do not lower risk because the request is small: schema, auth, external contracts and irreversible changes still select their applicable obligations. UI, telemetry, external collection and warehouse participation are independent choices; external collection does not imply telemetry or a warehouse.

**Uncertainty.** Record `uncertainty` on the work item from what can be observed now:

- `spike`: the deliverable is an answer to a stated question (feasibility, cost, performance). Time-box it and name the measurement that answers it. Its code is thrown away, never merged or promoted, so no spec, acceptance, release or deployment task is selected; building it for real is a new work item.
- `bounded`: the flow to change can be read in the repository today (files, call path, tests) and nothing that others consume changes. The ordinary create/refine/fix tasks apply.
- `architectural`: a new project or subsystem, or a change to an interface, schema, event or contract that others consume. Select architect shape/contract (an ADR for a hard-to-reverse choice) and the consumers' impact before implementation tasks.

The value only moves toward `architectural`. When work shows a heavier predicate holds (a bounded fix needs an interface change), stop that task, record the evidence and continue in a successor work item at the heavier value. Never lower it to drop tasks.

The product map stays coarse for future work. Detail the current slice's journeys, rules, permissions, exceptional states and acceptance criteria before handoff design. An exploratory prototype can answer an unresolved requirement earlier. High-level architecture/data feasibility can inform both; final UI-dependent contracts consume accepted design. API/data models are checked together before their consumers start. Complete implementation tickets only for the next executable slices, with one integration owner each.

Preflight follows the selected task: a requirement/design handoff needs resolved project/product roots and its actual inputs, not a running future application or release configuration. Create a minimal config with known `product_root` when needed; do not invent app/gate commands. Request or delegate only the configuration required for the next execution. Prototype rendering uses the prototype runtime; real application evidence uses the actual application. Product files are filled only when needed, with hypotheses labelled.

## Work records in the existing feature state

Use `task_protocol: 1` and include `work-scope-v1` in `required_capabilities`. Keep `selected_tasks` as the only task graph. `work_items` records why a set of tasks was selected and its stopping boundary; `active_work` is the resume pointer. It grants no file writes.

```yaml
active_work: requirements-r2
work_items:
  - id: requirements-r2
    kind: refine
    uncertainty: bounded
    intent_quote: "补齐退款权限和异常规则，停在需求确认"
    scope: "订单退款 FR-12 至 FR-15"
    target: "规则完整且可测试，需求版本已确认，可交给设计"
    tasks:
      - task: pm-spec-r2
        requires: accepted
    continuation: stop
    status: active
selected_tasks:
  - id: pm-spec-r2
    work_id: requirements-r2
    role: pm
    stage: define
    task: spec
    gate_stage: define
    selection:
      required: true
      reason: "补齐指定退款规则"
      source: "本次用户原话"
    depends_on: []
    attempt_kind: iteration
    rework_rounds: 0
    status: todo
```

Each work item requires `id`, `kind` (create/refine/fix), `intent_quote`, `scope`, `target`, nonempty `tasks`, `continuation` (stop/continue), and `status` (active/completed/cancelled). Fixes also require `origin`, naming the defect and original feature/build/release reference. `uncertainty` (spike/bounded/architectural) is optional; see Scope, target and risk. Cancellation needs `reason`; it is not completion. `tasks` rows use `task` and `requires: produced|accepted|verified`. A draft may stop at produced; an approved handoff needs accepted; a verified fix needs verified evidence and the applicable independent verification/acceptance tasks. Do not relabel a requested approval or verification as mere production.

New tasks belong to their `work_id`; existing completed protocol tasks can be referenced for reuse. Dependencies remain on the selected task instances. `work_items` and task rows use block mappings, not YAML flow objects. Seal the scope/target and each issued task's completion level with dispatch. Add required tasks or revalidation instances without changing those facts; changed scope/target or an issued completion level requires a successor work item, preserving or cancelling the prior request with a reason. Never remove issued tasks. A superseded task may close through an explicitly selected, completed successor of the same task contract; consumers still need their dependencies rebound and revalidated. Do not rewrite historical results.

`attempt_kind` is initial, iteration, rework, revalidation or fix. `rework_rounds` on that task counts consecutive failures of the same agreed quality criterion. In scoped work it replaces the legacy global counter for debug dispatch. User feedback, a new requirement and an ordinary design direction change are iterations; they do not consume the technical retry budget. A defect's first diagnosis can use debug immediately. Failed quality checks still use diagnosis/escalation proportional to the unresolved issue. From `rework_rounds: 3`, `prepare` requires a decision of kind `escalation`, recorded by someone other than the producing role. It targets a diagnosis file naming the route: reslice, change approach, reassign or stop. Bind it in `decisions` before another attempt. Escalation never resolves or waives open obligations.

## Execute and complete

Use `prepare → seal → record → check-tasks` for tasks whose registry declares `protocol_required` or `protocol_supported`. The latter preserves v2 compatibility outside a work item; scoped tasks use v3. Generated task inputs list the concrete contracts. Binding indexes are small versioned files; every referenced file actually consumed must also be declared through `supporting_inputs`. A path/URL in an index does not prove it was read or that a service ran.

Select the professional checks and independent review appropriate to the target and risk. Reviewer/QC keep their read-only v2 route and manager-persisted reports. Bind required acceptance/verification decisions to the exact producer result and target version, citing the independent report/owner authority. Never let a producer approve its own result. The scripts validate recorded evidence, not the truth of a human or agent's judgment.

```sh
python3 PLUGIN_ROOT/scripts/workflow.py check-work --root FEATURE --work-id requirements-r2
python3 PLUGIN_ROOT/scripts/workflow.py complete-work --root FEATURE --work-id requirements-r2 --out FEATURE/work/YYYY-MM-DD-requirements-r2-UNIQUE.json
```

Use the actual Beijing date and unique suffix. `bash PLUGIN_ROOT/scripts/check-sdlc.sh --work WORK_ID FEATURE` is the same scoped check and cannot be combined with `--hat`. Completion validates the selected results, their dependency chain, version-bound completion decisions and due obligations, and writes an immutable scoped-completion record. The manager copies the returned `result`, `result_sha256`, `status` into the work item and clears `active_work`. The command never updates state, `hats_done`, stage gates or `phase: Closed`. A completed work item remains a historical fact even if later changes make its result need revalidation.

For `coordinated-state-v1` states, perform that final binding through `continuous state-update` with the current state hash. Preserve the result if interrupted, then bind it after checking its identity; do not rerun the completed tasks. A stale state hash means re-read and reconcile, not overwrite.

Report the completed scope and versions, remaining stages, unresolved issues outside this scope, and the next available action. `continuation: stop` ends this request normally; do not mark it blocked. `continue` proceeds only within existing authorization and after applicable dependencies/gates. Feature completion, release readiness and deployment still require their existing aggregate gates and release evidence. `check-work` is never a replacement for `check-sdlc.sh` when claiming an entire stage/feature delivered.

## Change impact and reuse

Before edits, query both the task graph and requirement/artifact references:

```sh
python3 PLUGIN_ROOT/scripts/workflow.py impact --root FEATURE --task-id pm-spec-r2
python3 PLUGIN_ROOT/scripts/workflow.py trace FR-12 --feature FEATURE
```

These are read-only aids. Include all affected consumers and **previously passed** tests/acceptances, not just previous failures. Incomplete references mean broader artifact/owner review, not proof of no impact. Mark affected artifacts/gates stale; independent unaffected work may proceed. Product facts distinguish proposed, accepted, implemented and deployed versions.

A repeated completed task uses a new instance. If results remain correct, revalidation can inspect them and rerun applicable checks without rewriting implementation. File/source fingerprints are deliberately conservative; an unchanged output alone does not make changed inputs safe. A newer integration/build may need revalidation instances for earlier implementation evidence. Keep this cost visible; do not manufacture an exemption or erase the original result.

## Defect closure

Expected behavior may come from accepted requirements, API/schema invariants, an established behavior baseline or an explicit owner decision. Missing historical PRD/GWT does not force a full product bootstrap; record the narrow expectation and its authority. Ambiguous business expectations go to PM before repair; do not silently change the oracle.

Frontend/backend `implement/fix` contracts consume a defect and accepted behavior/technical baselines, with explicit source writes, checks and integration evidence. Other owners use the applicable migration/collection/warehouse task. QA performs reproduction-based verification and risk-based regression; PM/design acceptance participates when their behavior or experience is affected. A fix work item can stop after verified repair; deployment requires the separate authorized release path. Incidents use authorized mitigation first, then diagnosis and follow-up repair.
