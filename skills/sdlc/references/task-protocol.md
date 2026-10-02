# Feature task protocol 1

Registry schema 3 declares `required_capabilities`; unknown versions/capabilities fail closed. The runtime supports `input-contract-v1`, `result-v1`, `task-closure-v1`, `work-scope-v1`. The three original contracts require v3. Tasks marked `protocol_supported: 1` now have explicit inputs for design, architecture, schema, implementation, data, verification and acceptance; scoped work uses their v3 route, while legacy lanes may retain v2. Tasks without an input contract and product/cycle retain the [legacy v2 route](packet.md). See generated task-inputs and [work-scope](work-scope.md).

The manager runs these commands. They do not spawn agents, execute returned shell commands, accept decisions or advance workflow state.

```sh
python3 PLUGIN_ROOT/scripts/workflow.py migrate-tasks --root FEATURE
python3 PLUGIN_ROOT/scripts/workflow.py prepare --role pm --stage define --task spec --scope feature --root FEATURE --bindings /absolute/bindings.json --out FEATURE/2026-09-26-pm-draft.json
python3 PLUGIN_ROOT/scripts/workflow.py seal --draft FEATURE/2026-09-26-pm-draft.json
python3 PLUGIN_ROOT/scripts/check_packet.py /absolute/generated-run-packet.md
# Dispatch the validated generated packet, save the complete final message, then:
python3 PLUGIN_ROOT/scripts/workflow.py record --run /absolute/generated-run-manifest.json --return /absolute/saved-return.txt
python3 PLUGIN_ROOT/scripts/workflow.py check-tasks --root FEATURE --task-id pm-spec
# After independent review and applicable acceptance:
python3 PLUGIN_ROOT/scripts/workflow.py check-tasks --root FEATURE --stage define --closure
```

Use the actual Beijing date in filenames. The date above is an example, not a permanent prefix. Every sealed run gets `YYYY-MM-DD-HHMMSS+0800-role-task-unique`; manifest, packet, start, saved return and result share that prefix. Records are append-only by convention and cannot be overwritten by these commands. `state.yaml` and content-addressed version objects retain stable names. A hash detects accidental changes, not a malicious actor who can rewrite every file and its references.

## Selection and migration

`migrate-tasks` emits an inventory and missing work; it never invents historical timestamps, host observations or passes. A legacy state (no `task_protocol`) is listed read-only: each old row keeps its raw text with `form` `block`, `inline-legacy` or `unparsed`; nothing becomes a protocol entry, and a protocol state stays strict. The manager reuses verifiable evidence or reruns before setting a task done. Do not add `task_protocol: 1` to an empty historical selected_tasks list. Pilot task results need v3; unrelated old tasks continue through existing aggregate gates. A strict graph may include future tasks, but unverified historical entries cannot close a stage. Do not migrate a whole project's task history merely to dispatch one pilot.

```yaml
task_protocol: 1
required_capabilities: [input-contract-v1, result-v1, task-closure-v1]
selected_tasks:
  - id: pm-spec
    role: pm
    stage: define
    task: spec
    gate_stage: define
    selection:
      required: true
      reason: user requested this feature
      source: recorded user intent
    depends_on: []
    status: todo
obligations: []
```

IDs are stable instances, separate from registry task names. Use a new instance for a repeated completed task. Status is `todo|doing|done|blocked|skipped|superseded`; computed validity is `current|needs-revalidation|unverified|invalid`. Done requires a matching immutable `result` path and `result_sha256`. Designer/DBA tasks map to shape; change-impact selects one of its registered gate stages. Dependencies are block mappings with `task` and `requires: produced|accepted|verified`. Required acceptance cannot be downgraded. A skipped optional legacy task needs a reason and a version-bound skip decision. The three original required contracts prohibit skipping; choose applicability before selecting them, or preserve a superseded/cancelled history without declaring completion. Superseded needs a real successor; it does not make old consumers valid automatically.

Protocol-owned YAML sections support indented mappings/lists, scalar values and scalar flow lists (`[]`, `[a, b]`). Flow objects, duplicate fields, aliases/tags, tabs, complex keys and multiline scalars are rejected. Existing fields such as `roles_skipped: [architect, growth]` keep legacy syntax. The shared reader is `runtime_protocol.state_read`; use it before manager edits and again after saving. No parser silently repairs unsupported state.

## Binding contract

The JSON validators live in `runtime_protocol.py`, `task_runtime.py`, `task_state.py` and `evidence.py`; these fixed field sets are the executable schema. JSON rejects duplicate keys, NaN/Infinity and unknown fields. [task-inputs.md](task-inputs.md) is generated from the registry, not another source of truth.

| Field | Meaning |
|---|---|
| task_id, project_root, product_root | Selected instance and real absolute roots. Product root must match project config. |
| intent_quote, assignment | Existing user intent and concrete delegated work; no automatic expansion of authority. |
| inputs | Object keyed by contract ID; file values are absolute paths. Artifact/product bindings are checked against registered paths. |
| supporting_inputs | Additional read-only file dependencies as objects with id/path; each is pinned and checked for reuse. |
| deliverable_paths | Concrete files, relative to feature root or absolute in a validated owned root. No glob/directory or run-record write grants. |
| source_writes | Explicit relative project files/directories; trailing slash grants a subtree. No whole-project default. |
| product_writes, memory_file | Explicit owned product files and optional own memory file. Read-write product inputs must be listed here. |
| visuals, imagery | Optional registered kinds; generated packets add the corresponding procedure references and check commands. Declare concrete SVG/image/metadata outputs; execute the checks separately and bind their evidence when required. |
| explore_roots | Existing absolute search roots, not instructions to read directories wholesale. |
| slice_integrator | Required for implementation. When this role integrates, declare `03-impl/T-n-integration.md` too. |
| allowed_companion_skills, required_companion_skills | Bare method names. Required is a subset of allowed; default is empty, not all registry companions. From technical rework round 2, both must include debug (task-local counters in scoped work). |
| decisions | Absolute paths to version-bound decision JSON; recorded authority, not authenticated identity. |
| required_checks, check_records | Explicit expected check context and already executed records; no “latest file” selection. |
| execution_mode | `serial` (default), `concurrent`, `group`, or capability-gated `isolated`. Only serial windows or registered worktrees with live claims can prove task attribution; see continuous-work. |
| store_roots | Every configured external store root, for observation only; this grants no store writes. |

Binding indexes must declare the referenced files actually consumed as supporting_inputs; an index alone pins only its own text. Source-writing and execution-required tasks need actual bound checks on return.

PM example:

```json
{
  "task_id": "pm-spec",
  "project_root": "/project",
  "product_root": "/project/docs/product",
  "intent_quote": "Add an export for support leads",
  "assignment": "Define the agreed export behavior and observable acceptance criteria",
  "inputs": {"briefing": "/project/.sdlc/export/00-discover/briefing.md", "decisions": "/project/.sdlc/export/00-discover/decisions.md"},
  "deliverable_paths": ["01-define/spec.md"],
  "product_writes": ["/project/docs/product/strategy.md", "/project/docs/product/feature-map.md"]
}
```

L1 does not require a discovery briefing. L2+ can bind an already authorized customer brief/spec as the briefing; cite why its scope is sufficient in the decisions input. A 0→1 PM may fill its owned product templates (`allow_unfilled`) using labelled hypotheses; this does not create measured facts. When tracking applies, supply the metrics facts/proposal input; absence of historical measurements is explicit there. Backend data_definitions may document a justified absence of data changes; it must not omit a schema that the actual ticket consumes. These are professional judgments, not values a nonempty-file check proves correct.

Backend T-n normally binds the accepted contract. The separate frontend/backend `implement/fix` tasks bind accepted behavior and technical baselines plus a defect; they do not change the T-n contract. Only its registered `l2-short-spec` alternative allows an accepted spec at L2 with `path: short`; an acceptance decision still binds that exact spec. Conformance has no such shortcut. There is no `inputs_waived`, reason/by escape hatch, arbitrary condition expression or directory-as-text input. Cardinality is one per input; use a small versioned index document to point to necessary supporting files, and declare those dependencies before relying on them.

`prepare` saves a non-dispatchable draft and missing list. Missing conditions/facts block sealing. `--offline` remains a draft even if files exist. `seal` rechecks inputs, context, configured roots, contract and actual plugin working-tree content; changes require a new draft. It saves full content objects for supplied inputs/source and method files (256 MiB snapshot budget), plus before-write observations. Config checks are read-only; running checks/builds/apps occurs separately in authorized execution, with explicit evidence. No claim about a running build follows from a URL or source hash alone.

## Execution evidence and return

For a protocol check, provide context JSON to `evidence.py run --feature FEATURE --name CHECK --context CONTEXT.json -- COMMAND...`. Its fields are `check_id`, `scope`, `environment`, `executor`, `build` (null for source/static checks). Required checks in bindings are objects with `id`, `scope`, `environment`, `build_required` boolean. The record saves command, exit, times, project, full source identity before/after and log digest. A running-build requirement additionally needs build `id`, `source_sha256`, `association: verified`, `evidence` path and `evidence_sha256`. This checks the recorded association and preserved proof; independent review decides whether that proof establishes the claim.

Bind the exact execution record. Missing logs, mismatched contexts/source, changed-during-run, failure and a newer failure in the same check/source/environment all invalidate reuse. Old evidence records still serve legacy gates, but missing context fields are not fabricated to make them protocol passes. No default time-based freshness is claimed for live services; rerun a current observation when its environment/window changes.

The final message retains its summary, product delta, verified lessons and any full professional report. Append exactly one block:

```result
{
  "methods_used": [{"skill": "prd-gwt", "reason": "Mapped agreed value to observable behavior", "provenance": "reported"}],
  "reported_reads": ["briefing", "strategy", "feature_map", "decisions"],
  "unresolved": [],
  "proposed_changes": [],
  "product_delta": [],
  "lessons": [],
  "check_records": []
}
```

Unresolved entries require `id`, `owner`, `blocks` (task IDs), `item`, `severity: blocker|major|minor`. Proposed changes require `target`, `change`, `evidence_refs` (declared input IDs or output paths). Required methods must be reported used with reasons. These are model reports, not host trace. No host trace currently means `read_observations.host: null`, `level: unobservable`.

`record` runs registered presence checks and validates supplied execution records; it never runs commands in the return or packet. It saves incomplete/interrupted results as such (`--interrupted REASON`), and never edits a prior result. Missing output, malformed return, stale read input or observed unauthorized write prevents completion. A legal read-write post-version is an output and does not invalidate its own run. On recovery, preserve partial run directories and inspect them; a missing manifest cannot be dispatched or recorded as success.

## Reuse, obligations and closure

File-level dependency checking is conservative. A result can remain historically complete while current versions need revalidation. Later accepted successor versions require a `successor` decision binding old/new target digests and a complete successor result; do not overwrite the old result. Results alone do not mark state done.

Decision JSON fields are `id`, `kind: acceptance|verification|resolution|skip|successor|escalation` (escalation: [work-scope](work-scope.md), from `rework_rounds: 3`), `target`, `target_sha256`, `scope` (feature root), `by`, `authority`, `quote`, `at` (ISO 8601 time; `Z` and `+08:00` offsets are both accepted), `status: accepted`, `obligations` (empty only when none remain). Optional `result_sha256` links the applicable result; `supersedes_sha256` links an old artifact version. Resolution records use `result_sha256` to reference the proposing immutable result's digest, and target current resolution proof. Obligations in state carry `id`, `raised_by` (task ID), `owner`, `blocks`, `gate_stage`, `status: open|resolved`, and `resolution` for a resolved item. Deleting a blocker row does not erase the issue in the old result.

`check-tasks` without closure reports readiness/validity and ignores future todo work. `--task-id` checks prerequisites for that dispatch. `--stage ... --closure` checks the selected stage and its due obligations plus applicable recorded independent review (define/shape/implement/review; no new verify G-fresh is invented). Issued tasks, the definition producer and known backend tickets cannot disappear from the closing graph. Non-pilot participation remains checked by the existing aggregate gates. `check-sdlc.sh` retains professional, lane, product, acceptance and final review gates; Closed also invokes full task closure. A completed producer can therefore be sent to G-fresh without waiting for that same review to mark the producer done. No helper writes hats_done.

## Write observations

Observe project, feature, product and configured store roots, including dirty/untracked files and external roots. Record hashes, additions/deletions, symlink targets and modes; re-resolve sealed write targets at return. Only the manager's exact run-record paths are excluded; `.sdlc` as a whole is not excluded from this audit. Content snapshots do exclude caches/dependency directories, listed explicitly in every snapshot. Source identity has its separate exclusions and cannot substitute for this write audit.

Report task_observed for a manager-declared serial window or a registered isolated worktree with a valid claim. Use `record --concurrent` if another actor may have written in its observed workspace; group observations cannot prove individual compliance. Before/after snapshots cannot detect write-then-restore, remote effects or changes outside observed roots; gaps and limits remain in the result. This audits observed behavior; it does not enforce a filesystem sandbox. See [continuous-work.md](continuous-work.md) for `version_inputs`, `isolation`, `required_jobs`, external dependencies and fenced result import.
