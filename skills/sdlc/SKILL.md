---
name: sdlc
description: "Use this skill when the user says /sdlc, /sdlc-refine or /sdlc-fix, or wants SDLC delivery, refinement or defect repair. Manager window, never handoff. Do NOT use for $prd-gwt solo or L0."
when_to_use: "User asks for SDLC delivery, local refinement, defect repair or continuation. Do NOT use for a procedure skill invoked solo or a one-line L0 fix. Do NOT handoff the conversation to a hat."
---

# SDLC orchestrator (manager only) — v4

This **manager** keeps the conversation, classifies intent, coordinates state/context and dispatches specialists. Specialists load their assigned procedure with Skill (host Read fallback) in their own context. This window handles discovery and decisions, not role implementation.

Quality comes from product context, real evidence, early feasibility, explicit experience decisions and acceptance on the running build. Gates establish minimum checks; they do not replace professional judgment.

**Scope:** each `state.yaml` owns its feature/change tasks and work items; a derived project graph connects their versioned dependencies. Product iteration, repair and data work may coexist. `/sdlc-product` also maintains the product layer independently. Organizational portfolio, vendor/HR/legal process, CI platform ownership and production on-call remain outside this plugin. Cross-repository dependencies do not imply an automatic multi-repository deployment platform.

## Entry modes — resolve before Step 0

The command supplies `mode` and arguments. Without a command (Codex has no plugin commands; [references/hosts.md](references/hosts.md)), an explicit `mode: <m>` or the command name in the request selects that mode; otherwise `auto`.
- `product`: execute [references/product-mode.md](references/product-mode.md), then return. Do not initialize a feature lane.
- `review-only`: execute [references/review-mode.md](references/review-mode.md), then return. Report only; never advance feature state.
- `refine` / `fix`: resolve the object, target and scope with [work-scope.md](references/work-scope.md), then use the same task dispatch below.
- `auto`: classify intent below. If it resolves to product or review-only, use the same mode references and return.

Commands contain no procedures. Entry routing, role/stage/task mappings, artifact paths and ownership come from `workflow/registry.json`; [references/stage-map.md](references/stage-map.md) is its generated view. Read [references/stage-procedure.md](references/stage-procedure.md) for scheduling, inputs and participation. Before composing a packet run `python3 <PLUGIN_ROOT>/scripts/workflow.py contract --role <role> --stage <stage> --task <task>`; do not guess a role’s default skill for a different task.

## Iron rules

1. The hat that produces an artifact never approves it.
2. Rules a script cannot decide stay with the reviewer or a checklist, not in a gate.
3. Unused mechanisms are explicit `N/A` with a reason — never silent skips.
4. Role work never happens in this window — except Step 1b discovery HITL and presenting decisions (you present, the human decides).
5. Every hat reads the product layer first; every producing hat keeps its product files true and returns delta rows, which only you record (`product-delta.md`, `CHANGELOG.md`).
6. On a UI change, final architecture contracts consume the approved final design. Risky technical assumptions can be checked earlier with architect `define/feasibility`; that task does not choose the product experience or require a frozen spec.
7. Acceptance on the build before the final review: pm walks the journeys, the designer runs design QA, growth checks claims.
8. Strategic decisions belong to the operator. Reuse explicit authority; pending choices block their consumers, never become a hat's default.

## References and templates — read when

| File | Read when |
|---|---|
| [references/work-scope.md](references/work-scope.md) | A scoped target, local refinement, defect repair or resume; work completion and change impact |
| [references/continuous-work.md](references/continuous-work.md) | Version coexistence, cross-feature readiness, CAS state, isolated concurrent work, integration candidates or long data jobs |
| [references/stage-map.md](references/stage-map.md) | Filling any packet: roles, stages, deliverables, inputs, order, ranks, participation |
| [references/function-map.md](references/function-map.md) | Which roles and tasks a function covers (产品 / 运营 / 设计 / 研发 / 质量) |
| [references/product-layer.md](references/product-layer.md) | Step 0, `product_context` / `product_writes`, `/sdlc-product`, PRODUCTCTX or WRITEBACK failures |
| [references/orchestrator-gates.md](references/orchestrator-gates.md) | A spawn fails, resuming, G-fresh or acceptance fail, rework ≥3, host facts |
| [references/debug-loop.md](references/debug-loop.md) | Rework respawn with `rework_rounds >= 2` |
| [references/ops-vs-sre.md](references/ops-vs-sre.md) | The request says 运营 / 运维 / 增长 / ops / marketing |
| [references/role-agents.md](references/role-agents.md) · [references/subagent-design.md](references/subagent-design.md) | Changing how role prompts are built |
| [templates/sdlc.config.yaml](templates/sdlc.config.yaml) | The project has no config (gates incl. e2e, app start/base_url, product_root) |
| [templates/state.yaml](templates/state.yaml) | Starting or resuming a feature (v4 keys) |
| [references/state-records.md](references/state-records.md) | Persisting state, gate evidence or decision provenance |
| [templates/work-brief.md](templates/work-brief.md) | Durable intake and handoff for iteration, defects or investigation |
| [templates/product-readme.md](templates/product-readme.md) · [templates/product-changelog.md](templates/product-changelog.md) · [templates/cycle.yaml](templates/cycle.yaml) | Bootstrapping `product_root`; a product cycle |
| [templates/product-delta.md](templates/product-delta.md) | Every v4 feature (writeback record) |
| [templates/spec-s.md](templates/spec-s.md) | L1 / L2-short single-file spec |
| [templates/m/README.md](templates/m/README.md) | L3+ directory layout |
| [templates/role-memory.md](templates/role-memory.md) | Per-role notes under `<feature>/memory/<role>.md` |

## Plugin root

This file is `<plugin>/skills/sdlc/SKILL.md`; **PLUGIN_ROOT** is two directories up (the folder with `skills/`, `agents/`, `commands/`, `scripts/`). Resolve symlinks first — hosts reach the plugin through links ([references/hosts.md](references/hosts.md) §PLUGIN_ROOT); a host-exported root (`$ZCODE_PLUGIN_ROOT`) wins when set. Pass the absolute PLUGIN_ROOT in every packet; never hardcode a home path.

## Step 0 — init

1. Resolve the user's explicit scope/target before preflight or resume. Read `sdlc.config.yaml`; if absent, create only the known project/product-root settings. Run `check_config.py`, but gate only tasks that need each missing capability. Requirements do not need an app/E2E command, prototype design uses its own runtime, and actual build verification waits for the real app. Delegate authorized config changes to SRE ci; ask only for missing facts/authority.
2. **Product layer:** resolve `product_root` (default `docs/product`); initialize only the files the selected tasks need, never overwrite. New feature state gets `sdlc_version: 4`. Reuse evidence from an existing product; do not force a full bootstrap for a local change or bug.
3. **Resume:** explicit refinement, repair, review or a new scope wins over unfinished state. Bare continuation resumes `active_work`, otherwise unfinished feature tasks; a completed work item is not authorization to continue downstream. Preserve old states and normalize legacy hat words once. An unresolved failed review still blocks its affected dependents.
4. Note whether this host's role types exist ([references/hosts.md](references/hosts.md): `sdlc-workflow:<role>`, Codex/Kimi `sdlc-workflow-<role>`); if not, use the `host_spawn` fallback ([orchestrator-gates.md](references/orchestrator-gates.md) §1).

## Step 1 — intent (before any spawn)

Classify the user's **last substantive message**. Legacy lanes record `intent: {class, quote, at}`; scoped requests record their quote/kind in `work_items` without rewriting older tasks' authority:

| class | matches | manager action |
|---|---|---|
| `resume` | explicit/bare continuation with unfinished work | resume the active work or ready feature tasks |
| `refine` | revise/clarify a named requirement, design, schema or data artifact | select producers and checks through work-scope |
| `fix` | reproduce/repair/verify a defect | scoped diagnosis/repair/verification, linked to its baseline |
| `L0` | typo / one-line fix / "don't run the process" | commit trailer `lane=L0`; no state, no hats |
| `single-hat` | "write a PRD", "only design this screen" | Scoped work with the requested producer and completion proof; no whole swimlane |
| `review-only` | "independent review" | execute review-only mode |
| `product` | "build/refresh the product layer", "定位/核心功能/领域模型梳理" | execute product mode |
| `eval` | "run the eval" | refuse; a fresh window with `/sdlc-eval` |
| `out-of-slice` | org process / CI platform / on-call | refuse citing the scope paragraph |
| `discovery` | "先调研/先讨论", or an unresolved product decision | Step 1b |
| `new-feature` | gated delivery and briefing `done`/`skipped` | Step 2 |

An explicit stopping point can select one or several tasks through work-scope. Single-hat discipline: do not invoke `$prd-gwt` or any procedure skill here; do not inflate a single-hat request into a lane. "Also review it" → `/sdlc-review` after files land.

For an independent diagnosis, prototype, analysis, data audit or mining experiment, select its registered task and end at its local result. Triage feedback against the accepted behavior: changed goals create iteration; broken accepted behavior creates a defect; uncertainty creates investigation. Keep durable behavior/interfaces/acceptance in the work brief; expand concrete file paths and check commands against the actual execution snapshot. Facts that can be investigated are not questions for the user. Persist the source of unresolved decisions and block only their consumers.

## Step 1b — discover (before lane, before pm)

Separate uncertainty from size. Clarify bounded gaps and specialist-returned questions via the [discussion protocol](../discover/references/discuss-protocol.md), using the existing brief without new discovery state.

For substantial product uncertainty (check L2+ without a discovery result), invoke `sdlc-workflow:discover` → accept the slice in `00-discover/briefing.md`. Reuse accepted briefs/defects/decisions; select research as needed. No pm/architect/implement spawns or `spec.md` here. Partial readiness uses work-scope for independent authorized work, not full discovery completion. `killed` → stop; accepted slice + continuation authority → Step 2.

## Step 2 — lane and participation

Lane questions: **Q1** schema? **Q2** auth/tenant? **Q3** external contract? **Q4** irreversible? **Q5** new dependency? **Q6** files > threshold (default 20) or 2+ subprojects? Participation questions, recorded in state: **Q-ui** user-facing UI → `ui: yes|no`; **Q-tracking** new or changed events/metrics → `tracking: yes|no`. `q_security: yes` when Q2, Q3 or Q4.

Lane completion requirements are generated in [references/stage-map.md](references/stage-map.md). Apply participation and ordering from [references/stage-procedure.md](references/stage-procedure.md); selecting a lane does not dispatch every available agent. A skipped role needs a reason and does not remove aggregate stage requirements.

L2-short only follows the explicit eligibility predicate in [stage-procedure.md](references/stage-procedure.md); appetite or a short-path label alone cannot skip architecture.

## Step 3 — prepare and dispatch the selected task

Resolve the exact role/stage/concrete task in `workflow/registry.json`. Tasks with `protocol_required: 1` use [references/task-protocol.md](references/task-protocol.md): complete explicit task selection and bindings → `workflow.py prepare` → inspect missing prerequisites → `seal` immediately before dispatch → validate the generated v3 packet. Offline drafts cannot be dispatched. Keep each recorded task in an isolated execution window. Reuse recorded authorization; missing facts remain blocked, not waived.

Tasks declaring `protocol_supported: 1` also use v3 inside scoped work; their v2 path remains available for legacy lanes. Tasks without an input contract use [references/packet.md](references/packet.md), the explicit v2 route. Product and cycle retain their own commands; the new runtime rejects these scopes until evaluated. Apply task ownership, evidence, fresh-review boundaries and conditional debug rules on either route. Generated inputs are indexed in [references/task-inputs.md](references/task-inputs.md); scheduling remains in stage-procedure.

Use the host's dispatch schema and role mapping ([references/hosts.md](references/hosts.md)); packets keep `sdlc-workflow:<role>`. If the host cannot resolve it, make one fallback with the host's generic type (`general-purpose`; Codex `default`; Kimi `coder`) that reads that role's generated agent and primary procedure; record host_spawn. Do not dispatch both forms. Reviewer/qc need a fresh context with verified read-only permissions; block the review if unavailable. Record effective permissions ([orchestrator-gates.md](references/orchestrator-gates.md) §1). Return the full report; the manager persists it. Never give them producer memory or writable paths. For qc, run `skills/coverage-matrix/scripts/check-matrix.py` and supply its output.

After execution, save the full return and `record` it; bind the immutable result path and digest in state. Run `check-tasks` for task readiness, then existing independent reviews and acceptance, then `check-work` / `complete-work` for the scoped target, or `check-tasks --stage <gate_stage> --closure` when claiming a whole stage. Stage checks do not automatically advance state. All new packet/run/return/log filenames carry the actual Beijing date and a unique suffix.

For `coordinated-state-v1`, bind saved results through CAS instead of rerunning completed operations. Concurrent writers require registered disjoint worktrees, live resource claims and fenced import: follow [continuous-work.md](references/continuous-work.md). Ordinary concurrent/group observations cannot prove individual writes.

## Step 4 — human decision points (you present, the human decides)

- **Discovery freeze** (Step 1b).
- **Design direction pick** (`ui: yes`): when a new direction decision is needed, after designer `explore`, show each direction in one line — signature moment, trade-off, screenshot paths — plus the designer's recommendation, and wait only if the decision is not already authorized or delegated. Record `design: {picked: D<n>, picked_by: user|delegated, at}`. The designer's `specify` spawn writes `选定：D<n>` into `design-directions.md`.
- **Strategic decisions** (`Q-*`, 类别 战略, 状态 待确认): use the discussion protocol to present manageable, dependency-ready choices with options and recommendations. Name the decider from `owners` if configured. Reuse explicit authority; silence or an unanswered tool is not consent. "按推荐" or "你定" is an answer; record its scope in `open_questions` (Step 5) and respawn the owner to write 已确认 with the operator's words. Pending choices block their consumers; unrelated ready work continues. Use `phase: Stopped` only when no authorized work can proceed.
- **Operational defaults** (状态 默认): list them in your report; the user can overturn any of them later.
- **Acceptance** verdict `有条件通过`: the user accepts the conditions or sends the slice back. Record acceptance as `open_questions` entry `{id: Q-ACCEPT-<PM|DESIGN|GROWTH>, status: answered, by: user, quote: "<their words>"}`; the gate checks it.

## Step 5 — state.yaml

Update after each task using [state-records.md](references/state-records.md) for field enums, evidence and decision provenance. The task graph and work_items govern readiness; current_hat is a display/resume hint. Scoped completion does not add hats_done or set Closed. Record actual execution evidence, authorized decision quotes and product deltas; historical completion remains separate from current validity. Use CAS for coordinated states and never overwrite a stale revision.

## Step 6 — gates

After each task, run its `workflow.py check-task` presence check and the owning skill’s checks. Only after all participating tasks in a stage have returned, run the stage gate below. In particular, partial-stage tasks use their own checks: designer explore needs no specify artifacts, and architecture feasibility needs no completed spec. Follow stage-procedure for change impact and conformance; a completed report does not settle pending decisions or unverified obligations. Task success never alone adds `shape` or `accept` to `hats_done`.

- **G-script:** the config commands (test / lint / build / migration / e2e) + `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --require --hat <stage> <feature-dir>`. Agent said so ≠ file exists — `ls` first. Plain runs skip with exit 0; `--require` / `--hat` turn a missing file into a failure.
- **G-fresh (L1+):** once per stage after all its producers return (define; shape = designer + architect + dba + invited data hats; implement), plus the final review after accept. The reviewer packet carries artifact paths and the product files named in `product-delta.md` — never your reasoning. Fail (blocker/major unwaived) → producer rework, `current_hat` stays; `review` enters `hats_done` only after the final review passes. L1: the implement G-fresh is the review. Same snapshot, criteria, scope and relevant evidence → reuse `findings.md`; `/sdlc-review` is the report-only entry to the same reviewer.
- **Acceptance (v4):** every participating `accept-*.md` ends with `结论：通过 | 有条件通过 | 不通过`. Any `不通过` → classify the gap and route to its owning producer; implementation defects return to implement, requirement/design problems to their owners. Re-run affected verification and acceptance, including prior passes whose inputs changed.
- **Decisions (v4):** `DECISIONPENDING` is not rework — ask the operator (Step 4). `DEFAULTED` is rework on the producer: the strategic call goes back to 待确认 with options before you ask ([orchestrator-gates.md](references/orchestrator-gates.md) §10).
- **G-self (L3/L4, one pass):** scope, irreversibility, cost, and launch timing vs capacity.
- **Rework with method:** repeated failure against the same agreed criterion uses the task-local `rework_rounds` in scoped work (legacy lanes retain the global counter). From round 2 attach debug for technical rework and record the mechanism. Three consecutive failures require diagnosis/escalation; normal user-driven iteration/revalidation does not consume this budget. See work-scope and [debug-loop.md](references/debug-loop.md).

## Memory = artifacts

Subagents start from files, not your chat. `state.yaml` is the resume map; the product layer is the product's memory; an upstream change marks downstream artifacts `stale` and re-runs the failed gate.

## Metrics

Per feature: acceptance first-pass rate, E2E pass on core journeys, escapes, rework rounds, gate intercepts, spawn count. Judge a gate by risk coverage, escapes, cost and intercepts — zero intercepts alone never justifies removal. Spawn count is a cost to explain, never a reason to skip the designer, dba, growth or acceptance.

## Task scope

Apply [task-scope.md](references/task-scope.md) for project profile, delivery goal and source write boundaries. These scope records do not bypass lane gates.
