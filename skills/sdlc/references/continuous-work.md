# Continuous work: local targets, versions and coordination

Read this when several work items coexist, when consuming a stable older artifact, or when executing isolated concurrent work. Ordinary single-task work keeps the existing work-scope protocol. The manager owns these operations; they do not grant authority to deploy, contact people, change production data or waive review.

## Entry and durable context

User language remains `/sdlc` plus the object and stopping point: “only locate the missing records”, “keep implementing v1 while refining v2”, “analyze snapshot D20”, “repair and verify without releasing”. Select only the relevant tasks. `retro/analyze` is callable at any lifecycle point; its stage label does not require a launch first.

Use [work-brief.md](../templates/work-brief.md) when feedback needs a durable handoff. Keep the original request, classification, accepted behavior, desired change, boundaries, completion proof, decision sources and affected consumers. Reference existing facts. Do not prewrite all implementation code. Add it to the task's `supporting_inputs`; `prepare` expands the concrete files/checks against the execution snapshot.

Historical task completion, current validity and acceptance/verification are separate. A new proposal creates a new version or successor instance. An inconclusive investigation can finish its bounded question; it cannot claim a repair. Never turn a feedback loop into a cyclic task-instance dependency.

## Capabilities and operations

Retain `task_protocol: 1` and the old capabilities. Add only the capabilities used by the state: `artifact-versions-v1`, `project-graph-v1`, `coordinated-state-v1`, `isolated-execution-v1`, `candidate-v1`, `data-jobs-v1`. New cross-feature/isolated states also need a stable `project_id`. Unknown capabilities fail closed. Do not rewrite historical run records.

Manager operations use one CLI and an inspectable JSON request:

```text
python3 <PLUGIN_ROOT>/scripts/workflow.py continuous <operation> --request /absolute/request.json
```

Each request is a JSON object with the named arguments below. Paths are absolute unless expressly feature-relative. The command prints structured output and does not silently advance the next stage.

| Operation | Request arguments | Meaning |
|---|---|---|
| `state-update` | `root`, `expected_sha256`, `updates` | CAS update of protocol-owned state sections; stale readers cannot overwrite current state |
| `bind-result` | `root`, `task_id`, `result_path`, `expected_sha256` | Bind an already saved native result; retry after interruption without rerunning work |
| `artifact-capture` | `root`, `logical_id`, `source`; optional `artifact`, `producer_task`, `product_file` | Freeze a feature artifact or an owned product file as an immutable version |
| `artifact-promote` | `ref`, `expected_sha256`, `decision_path` | Accepted version becomes current pointer; preserve promotion history |
| `project-ready` | `roots`; optional `changed`, `coordinator` | Rebuild the graph, report readiness/reasons and declared downstream impact |
| `workspace-register` | `project`, `workspace_id`, `workspace`, `canonical_feature`, `feature_root`, `product_root` | Register an existing disjoint worktree belonging to the same repository |
| `claim` | `project`, `key`, `owner`, `workspace`, `resources`; optional `ttl` | Atomically claim a task and resources; return fencing token |
| `heartbeat` | `project`, `key`, `token`; optional `ttl` | Extend an active lease |
| `release-claim` | `project`, `key`, `token`, `reason`; optional `reconciled` | Release after completion or verified process/job reconciliation |
| `import-result` | `project`, `workspace_id`, `task_id`, `result_path`, `token`, `expected_state` | Bind an isolated result to its canonical task under a live token |
| `candidate-create` | `project`, `root`, `product`, `candidate_id`, `base`, `components`, `checks`; optional `versions` | Pin the exact integration source and component results |
| `candidate-verify` | `path`, `records`; optional `approvals`, `release` | Verify the exact candidate; release readiness still is not deployment |
| `dataset-capture` | `root`, `dataset_id`, `source`, `semantics`, `window`; optional `limitations` | Freeze a small dataset without following changes to the live source |
| `job-request` | `project`, `key`, `plan` | Persist a named job operation before submission |
| `job-start` / `job-status` / `job-reconcile` | `ref`; optional `timeout` | Submit once, query exact job, or recover an uncertain launch by operation ID |

`expected_sha256` is the actual SHA-256 of the current `state.yaml` or artifact pointer. For the first artifact promotion use JSON `null`. `ref` means `{"path":"/absolute/record.json","sha256":"<actual file digest>"}`. Hashes are measured, never supplied from memory. A state update increments `state_revision`, preserves unrelated legacy fields and cannot remove issued tasks, historical results or obligation history. All cooperating managers use this API. Direct file edits bypass coordination and are not safe for concurrent managers.

## Versioned inputs and product proposals

`artifact-capture` saves bytes under the owner's `.task-objects` and returns a record reference. Use `artifact` for a registered feature artifact type; use `product_file` for the product-relative owned file. Attach `producer_task` to link a version to its completed producer. Imported pre-existing baselines have no fabricated producer run.

The optional `bindings.version_inputs` maps registered input IDs to version references. Do not also bind the same ID in `inputs`. Versions can fulfil read-only binding/artifact/product inputs; a read-write product task must use an isolated product copy or its normal single-writer path. For an accepted input the reference also names `decision`, a recorded acceptance targeting the immutable object in the owner feature scope. Acceptance records are authority assertions with quotes, not authentication of the person named.

Example binding shape:

```json
{
  "version_inputs": {
    "accepted_contract": {
      "path": "/project/.sdlc/schema/artifacts/catalog-contract/version.json",
      "sha256": "measured-record-digest",
      "decision": "/project/.sdlc/schema/decisions/contract-accepted.json"
    }
  }
}
```

These are shape examples, not runnable placeholder evidence. `artifact-promote` checks the previous pointer and explicit acceptance before publishing. A new proposal does not overwrite old versions. Fixed product files remain human-readable projections maintained by their owner; promotion does not silently copy a proposal over them. Two competing proposals require a decision, not last-writer-wins.

## Cross-feature dependencies

Task-local `depends_on` remains unchanged. A selected task may add `external_dependencies` entries:

```json
{
  "feature_root": "/project/.sdlc/schema",
  "project_id": "catalog",
  "task": "schema-v5",
  "result_sha256": "measured-producer-result-digest",
  "requires": "accepted"
}
```

An optional `version` reference allows consuming an immutable producer artifact despite a later live-file revision. The version must link that producer result; `accepted` needs its bound acceptance. A snapshot cannot substitute for current behavior `verified`. Without `version`, normal current-validity checks apply.

`project-ready` takes explicit feature roots and follows these references. `changed` is `/absolute/feature#task-id`; its result includes earlier accepted/verified consumers. No persistent second task-state database is created. The index is rebuildable. Include `coordinator` to show active/expired claims. With `changed`, completed results among the listed roots whose recorded inputs read an affected output are added as `undeclared_consumers`; completed results that cannot be read are `unverified_consumers`/`unreadable_affected`. `impact_complete: false` means the impact boundary is open. Declare the missing edge or revalidate; never report "no impact". Consumers outside the listed roots and non-protocol readers (SQL, code imports) still need trace, reference search and owner review. Resource availability is finally checked atomically at claim time.

## Interruption and isolated execution

For an inserted request, preserve original task/version/working differences and create the new scoped work. Resume only after checking whether its inputs changed. A bare continue follows the session's active work; ask for selection only when several goals are equally plausible. A query or new opinion does not cancel previously authorized work.

For real concurrent writes:

1. Keep the canonical feature state in the coordinator checkout. Create separate Git worktrees at explicit bases using the project's normal tooling. They must be disjoint from the coordinator and each other. Copy only the required feature context and product baseline; preserve logical project/task identities. Initialize the worktree's config to its isolated product root. Do not copy stale active run directories.
2. Register each worktree. Feature and product roots must both be inside it; externally writable file stores require serial execution or another evaluated adapter. Worktrees share Git administrative storage: avoid Git commits/branch mutations by workers during an observed run; integrate through the manager after recording.
3. Claim `key=/canonical/feature#task-id`. Resources are objects `{"id":"db/catalog/partition-2026-09","mode":"write"}`. Hierarchical overlap conflicts when either side writes; reads can coexist. Use the same canonical IDs for the same database/API/environment. The workspace write claim is automatically included. Declare external resources honestly; the claim is not an OS or database permission boundary.
4. In bindings set `execution_mode: isolated` and `isolation: {coordinator, workspace_id, key, token, owner}` from the claim. Prepare/seal in the worktree feature. Heartbeat from the coordinator while the task runs. Other worktrees' writes are outside its observation root; input hashes and this task's full write audit still apply.
5. Record the return in that worktree. Import its result with the claim token and expected canonical state digest, then release. The importer validates repository/workspace identity, canonical task context, result/manifest hashes and token. A stale return cannot update the new owner's state.
6. On lease expiry, query processes/jobs first. Save checkpoints/results. Release with `reconciled: true` and a concrete reason only after establishing what remains active; then reassign. Expiry never kills a process or proves failure. A result saved before a state-update interruption can be imported again with the current state digest while the claim remains active.

Claims record a hashed machine identity. Check, heartbeat, release and new claims fail on another machine: file locks and leases are only local, so cross-machine coordination is unsupported until a shared lease store is evaluated.

The coordinator checkout can also run one serial task while worktree tasks proceed. Its claim, heartbeat, release and import records live in its `.sdlc/control`, which that serial task observes. Run those operations before sealing the serial task or after recording it. Otherwise, move the serial task into its own worktree too. To version an isolated output after import, run `artifact-capture` on the canonical feature with `producer_task`. The source path stays in the worktree, and the imported result must own that exact content.

A repair changes the source that its diagnosis observed. The diagnosis stays `needs-revalidation` because it describes older code. It carries `source_drift_from` when every source change since it ran equals what completed downstream tasks recorded writing. Those writers, their consumers and work completion that includes them may rely on it. An unrecorded edit, or a consumer outside that chain, still needs revalidation.

Keep registered worktrees, their manifests, objects, outputs and raw logs available after import. Import records reference that original evidence; they are not a portable archive. Do not delete or reuse a registered worktree while its results support a dependency or candidate. A future archival adapter must preserve and revalidate those identities before cleanup.

This implementation supports cooperating local processes on a local filesystem, not distributed consensus or arbitrary network filesystems. Product acceptance, shared DB migration and candidate integration remain single-writer operations per resource. Parallel root-cause research does not require parallel production writes.

## Exact candidates and release scope

`candidate-create` operates on the actual integration checkout. `base` is its explicit trusted Git baseline, not a floating latest branch. The manager must establish that baseline's accepted scope. Components are `{root, task, result_sha256}`. Their selected dependency/obligation checks must pass; source outputs must exactly match candidate files, and all source changes since base must be accounted for. Conflicting outputs require a separately recorded integration task. Removing a component from a list cannot hide its changed code.

`checks` uses the existing `{id, scope, environment, build_required}` execution contract; scope is the candidate ID and at least one check has `id: integration`. Prepare the final source/build state before defining the candidate, run its checks through `evidence.py`, then verify. A changed source snapshot or newer failed execution invalidates the claim. Symlinks are pinned by their link text and must equal the base, since components cannot change them. Links that leave the repository appear in `external_links`: the candidate pins the link, not the content it reaches, so verify that content separately when it matters. Submodules fail explicitly; use an evaluated adapter rather than skipping source coverage.

Verification accepts paths to real check records. Optional `approvals` are `{purpose, path}` records targeting the exact candidate manifest. `release: true` requires product acceptance, independent quality verification and operations readiness, with purposes `product`, `quality`, `operations`, plus a build-bound execution check. They cover applicable security, migration, rollback and acceptance obligations. Identity/independence of decision-makers still needs the normal recorded authority review. The result is `release-ready`, never `deployed`. Existing full-lane gates still apply when claiming an entire lane complete; a scoped candidate does not close unrelated active work.

## Data versions and long operations

The new analysis/audit/backfill/mining tasks require a dataset descriptor in their `dataset` input. `dataset-capture` freezes small files within the version-object budget. Its descriptor records semantics, observation window and limitations; file identity alone does not establish data quality.

For external/large data, use schema version 1, kind `dataset-snapshot`, a stable `id`, `semantics`, `window`, `limitations`, and `identity` containing `type: external`, `provider`, immutable `snapshot_id`, `partitions`, `query_sha256`, `observed_at`, and `evidence` file references with measured hashes. The platform adapter must support those snapshot claims. Do not use `latest` or a mutable table name as a snapshot. Preserve schema/metric/label/feature definitions in the descriptor or bound definitions input.

Job plans contain `environment`, `dataset`, absolute `cwd`, `intent_quote`, `start_argv`, `status_argv` and optional `lookup_argv`. They execute without a shell. The start adapter must consume `{operation_id}` and enforce idempotency remotely; status consumes `{job_id}`. Each adapter returns JSON `{job_id, status, result_refs}` with optional `checkpoint`. Status is submitted/running/succeeded/failed/cancelled/unknown. Adapters redact secrets and sensitive data from captured output.

The manager first records `job-request`, then submits through `job-start`. A durable start intent prevents accidental resubmission after a crash. Unknown launch outcome requires lookup by operation ID; it is not permission to call start again. Poll actual jobs and retain observations. A task binding may add `required_jobs: [ref]`; result collection rejects unfinished/unknown jobs. Terminal success additionally needs result references and the task's actual data validation checks. Query success or scheduler submission alone is insufficient.

Keep submission/status bookkeeping in the coordinator outside an isolated worker's observation root. For serial work, poll before sealing the downstream validation task, then bind its completed job. Mutating manager job records inside a sealed serial task's observed checkout is still an unauthorized write; job support does not exclude the whole `.sdlc` tree from auditing.

During backfill, readers consume a frozen snapshot/window. New validated partitions or corrected labels create a successor dataset/analysis/experiment; history remains intact. Expand schema first, migrate consumers and reconcile writes/backfill, then contract only after old consumers exit. Small projects can use a database and files without a warehouse platform.

## Evaluation and remaining boundaries

Run `test_continuous_work.py` for protocol scenarios and the normal repository checks. Use the existing eval protocol for repeated model-behavior comparisons and a user-selected real project for the mixed iteration/repair/data pilot. Protocol tests cannot claim model-level improvements or production readiness. Track incorrect reuse/completion, unrelated blocking, duplicate work, recovery, integration rework and user interruptions, with a pre-change baseline.

Each prepared run also records its `method_closure`. The closure covers the role file, every referenced skill directory (whole), the specific plugin files it links or names, the task's registered reads, the registry and all scripts. When another plugin file changes, a completed result stays current only if the closure was complete and its digest is unchanged. A link leaving the plugin makes the closure incomplete. Runs recorded before closures existed keep the whole-plugin rule. A plugin change during a run still invalidates that run. Source snapshots stay whole-project. Immutable artifact/data consumers reduce live-file drift where identity is explicit. Do not remove broad checks merely to make a continuous scenario green. Disable new operations to roll back behavior; retain their immutable results and capabilities so old runners reject unsupported state instead of pretending it succeeded.
