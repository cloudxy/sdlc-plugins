---
name: sdlc
description: "Use this skill when the user says /sdlc or continue last SDLC task. Manager window. Do NOT use for $prd-gwt solo or L0. Do not handoff."
when_to_use: "User says /sdlc, follow the process, continue last task, or wants gated swimlanes. Do NOT use for a single-role task ($prd-gwt etc.) or a one-line L0 fix. Do NOT handoff the conversation to a hat."
---

# SDLC orchestrator (manager only) — v4

This window is the **manager** (agents-as-tools): specialists run as nested spawns and you keep the user-facing reply. Do not handoff the conversation to a hat. You classify intent, keep `state.yaml` and the product layer, fill spawn packets, run gates, and run the human decision points. You never write specs, designs, schemas or code (Iron rule 4). Hats load their procedure skills (`prd-gwt`, `design-contract`, `architecture`, `schema`, …) with the Skill tool inside their own context — this window invokes only `sdlc-workflow:discover` in Step 1b.

**What v4 optimizes for:** a product worth using, not artifacts that pass gates. Gates are the hygiene floor. Quality comes from the product layer every hat reads first, diverge-then-converge work with real evidence, early technical feasibility and experience design before final architecture contracts, and acceptance on the running build.

**Slice:** one feature change per `state.yaml`, plus the product layer it reads and writes back (`/sdlc-product` maintains the layer on its own). Not an organizational SDLC: no portfolio intake, vendor/HR/legal process, CI platform or registry ownership, production on-call, multi-repo release trains. Refuse those by quoting this paragraph.

## Entry modes — resolve before Step 0

The command supplies `mode` and arguments. Without a command (Codex has no plugin commands; [references/hosts.md](references/hosts.md)), an explicit `mode: <m>` or the command name in the request selects that mode; otherwise `auto`.
- `product`: execute [references/product-mode.md](references/product-mode.md), then return. Do not initialize a feature lane.
- `review-only`: execute [references/review-mode.md](references/review-mode.md), then return. Report only; never advance feature state.
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
8. Strategic decisions belong to the operator. No explicit answer, no decision: stop and wait — never adopt a hat's recommendation as a default.

## References and templates — read when

| File | Read when |
|---|---|
| [references/stage-map.md](references/stage-map.md) | Filling any packet: roles, stages, deliverables, inputs, order, ranks, participation |
| [references/function-map.md](references/function-map.md) | Which roles and tasks a function covers (产品 / 运营 / 设计 / 研发 / 质量) |
| [references/product-layer.md](references/product-layer.md) | Step 0, `product_context` / `product_writes`, `/sdlc-product`, PRODUCTCTX or WRITEBACK failures |
| [references/orchestrator-gates.md](references/orchestrator-gates.md) | A spawn fails, resuming, G-fresh or acceptance fail, rework ≥3, host facts |
| [references/debug-loop.md](references/debug-loop.md) | Rework respawn with `rework_rounds >= 2` |
| [references/ops-vs-sre.md](references/ops-vs-sre.md) | The request says 运营 / 运维 / 增长 / ops / marketing |
| [references/role-agents.md](references/role-agents.md) · [references/subagent-design.md](references/subagent-design.md) | Changing how role prompts are built |
| [templates/sdlc.config.yaml](templates/sdlc.config.yaml) | The project has no config (gates incl. e2e, app start/base_url, product_root) |
| [templates/state.yaml](templates/state.yaml) | Starting or resuming a feature (v4 keys) |
| [templates/product-readme.md](templates/product-readme.md) · [templates/product-changelog.md](templates/product-changelog.md) · [templates/cycle.yaml](templates/cycle.yaml) | Bootstrapping `product_root`; a product cycle |
| [templates/product-delta.md](templates/product-delta.md) | Every v4 feature (writeback record) |
| [templates/spec-s.md](templates/spec-s.md) | L1 / L2-short single-file spec |
| [templates/m/README.md](templates/m/README.md) | L3+ directory layout |
| [templates/role-memory.md](templates/role-memory.md) | Per-role notes under `<feature>/memory/<role>.md` |

## Plugin root

This file is `<plugin>/skills/sdlc/SKILL.md`; **PLUGIN_ROOT** is two directories up (the folder with `skills/`, `agents/`, `commands/`, `scripts/`). A host-exported root (`$ZCODE_PLUGIN_ROOT`) wins when set; Codex runs an installed copy ([references/hosts.md](references/hosts.md)). Pass the absolute PLUGIN_ROOT in every packet; never hardcode a home path.

## Step 0 — init

1. Read `sdlc.config.yaml` (or copy the template and ask for: constitution, gate commands including `e2e`, `app.start` / `app.base_url`, `product_root`). Run `python3 <PLUGIN_ROOT>/scripts/check_config.py --project-root <root>`: blockers go to the user with the suggested block (delegate approved project-config changes to the scoped SRE ci task), and stages requiring a real UI build wait until it runs; early design may run its own prototype ([orchestrator-gates.md](references/orchestrator-gates.md) §12).
2. **Product layer:** resolve `product_root` (default `docs/product`). Copy missing templates per [product-layer.md](references/product-layer.md) — never overwrite. A new feature's `state.yaml` gets `sdlc_version: 4` and `product_root`. If the layer is mostly unfilled and the product already exists, recommend `/sdlc-product` before the first feature.
3. **Resume:** an unfinished `<artifact_root>/.sdlc/*/state.yaml` → class `resume`. Normalize legacy Chinese hat words once. Last fresh-context `fail` → stay on the producing hat (HATADVANCE).
4. Note whether this host's role types exist ([references/hosts.md](references/hosts.md): `sdlc-workflow:<role>`, Codex `sdlc-workflow-<role>`); if not, use the `host_spawn` fallback ([orchestrator-gates.md](references/orchestrator-gates.md) §1).

## Step 1 — intent (before any spawn)

Classify the user's **last substantive message** into `state.yaml` `intent: {class, quote, at}`:

| class | matches | manager action |
|---|---|---|
| `resume` | unfinished feature, not "new feature" | continue at `current_hat` |
| `L0` | typo / one-line fix / "don't run the process" | commit trailer `lane=L0`; no state, no hats |
| `single-hat` | "write a PRD", "only design this screen" | ONE producer spawn; no swimlane, no G-fresh |
| `review-only` | "independent review" | execute review-only mode |
| `product` | "build/refresh the product layer", "定位/核心功能/领域模型梳理" | execute product mode |
| `eval` | "run the eval" | refuse; a fresh window with `/sdlc-eval` |
| `out-of-slice` | org process / CI platform / on-call | refuse citing the slice paragraph |
| `discovery` | "先调研/先讨论", or an unresolved product decision | Step 1b |
| `new-feature` | gated delivery and briefing `done`/`skipped` | Step 2 |

Single-hat discipline: do not invoke `$prd-gwt` or any procedure skill here; do not inflate a single-hat request into a lane. "Also review it" → `/sdlc-review` after files land.

## Step 1b — discover (before lane, before pm)

When class is `discovery`, or `new-feature` at L2+ without `discovery.status: done|skipped|killed`: invoke `sdlc-workflow:discover` in this window and follow it — select the unresolved decisions and relevant evidence tracks using discover → freeze `00-discover/briefing.md`. No pm, architect or implement spawns in this step; no `spec.md`. Reuse accepted briefings, defect reports, contracts and explicit scope decisions; record the reference and why further discovery is unnecessary. Verdict `killed` → stop. After freeze and a current or prior authorization to continue → Step 2.

## Step 2 — lane and participation

Lane questions: **Q1** schema? **Q2** auth/tenant? **Q3** external contract? **Q4** irreversible? **Q5** new dependency? **Q6** files > threshold (default 20) or 2+ subprojects? Participation questions, recorded in state: **Q-ui** user-facing UI → `ui: yes|no`; **Q-tracking** new or changed events/metrics → `tracking: yes|no`. `q_security: yes` when Q2, Q3 or Q4.

Lane completion requirements are generated in [references/stage-map.md](references/stage-map.md). Apply participation and ordering from [references/stage-procedure.md](references/stage-procedure.md); selecting a lane does not dispatch every available agent. A skipped role needs a reason and does not remove aggregate stage requirements.

**L2-short predicate (closed set) — skips only the architect:** (a) `intent.skip_shape: true` and `02-shape/contract.md` already on disk; or (b) the implement packet marks the contract `required: false` and names `spec.md` as its substitute. `path: short` or appetite < 4h alone is not enough.

## Step 3 — prepare and dispatch the selected task

Resolve the exact role/stage/concrete task in `workflow/registry.json`. Tasks with `protocol_required: 1` use [references/task-protocol.md](references/task-protocol.md): complete explicit task selection and bindings → `workflow.py prepare` → inspect missing prerequisites → `seal` immediately before dispatch → validate the generated v3 packet. Offline drafts cannot be dispatched. Keep each pilot in an isolated execution window. Reuse recorded authorization; missing facts remain blocked, not waived.

Other tasks use [references/packet.md](references/packet.md), the explicit v2 route. Product and cycle retain their own commands; the new runtime rejects these scopes until evaluated. Apply task ownership, evidence, fresh-review boundaries and conditional debug rules on either route. Generated inputs are indexed in [references/task-inputs.md](references/task-inputs.md); scheduling remains in stage-procedure.

Spawn the host's role type ([references/hosts.md](references/hosts.md)); packets keep `sdlc-workflow:<role>`. If the host cannot resolve it, make one fallback with the host's generic type (`general-purpose`; Codex `default`) that reads that role's generated agent and primary procedure; record host_spawn. Do not dispatch both forms. Reviewer/qc remain read-only and return their full report; the manager persists it. Never give them producer memory or writable paths. For qc, run `skills/coverage-matrix/scripts/check-matrix.py` and supply its output.

After execution, save the full return and `record` it; bind the immutable result path and digest in state. Run `check-tasks` for task readiness, then existing independent reviews and acceptance, then `check-tasks --stage <gate_stage> --closure`. Stage checks do not automatically advance state. All new packet/run/return/log filenames carry the actual Beijing date and a unique suffix.

## Step 4 — human decision points (you present, the human decides)

- **Discovery freeze** (Step 1b).
- **Design direction pick** (`ui: yes`): when a new direction decision is needed, after designer `explore`, show each direction in one line — signature moment, trade-off, screenshot paths — plus the designer's recommendation, and wait only if the decision is not already authorized or delegated. Record `design: {picked: D<n>, picked_by: user|delegated, at}`. The designer's `specify` spawn writes `选定：D<n>` into `design-directions.md`.
- **Strategic decisions** (`Q-*` rows with 类别 战略, 状态 待确认): ask all of them in one round — question, options, the hat's recommendation — and **wait**. Name the decider from `owners` if configured (product-layer § Decisions). Only an explicit answer counts. Silence, a question tool that returns no answer, or a question the user never saw is not consent. "按推荐" or "你定" from the user is an answer; record it as such. Record each answer in `open_questions` (Step 5) and respawn the owner to write 已确认 with the operator's words. No answer → the dependent stage does not start: `phase: Stopped`, reason `waiting-for-operator`, and tell the user what is waiting.
- **Operational defaults** (状态 默认): list them in your report; the user can overturn any of them later.
- **Acceptance** verdict `有条件通过`: the user accepts the conditions or sends the slice back. Record acceptance as `open_questions` entry `{id: Q-ACCEPT-<PM|DESIGN|GROWTH>, status: answered, by: user, quote: "<their words>"}`; the gate checks it.

## Step 5 — state.yaml

Update after every hat. `current_hat` / `hats_done` use English words from the stage map. `phase` holds only the persistent enum (`Intent|Discovering|LaneJudge|HatReady|Spawned|Rework|HatDone|Closed|Stopped|Refused|L0done`). v4 keys: `sdlc_version: 4`, `product_root`, `ui`, `tracking`, `design`, `discovery.tracks.growth`. Gate kinds: `script | fresh-context | self-review`; `result: null` needs `reason`. Run E2E through `python3 <PLUGIN_ROOT>/scripts/evidence.py run --feature <feature_dir> --name e2e -- <e2e command>` and paste the gate record it prints (with `evidence:`); a pass without a current run record, or an older pass after a newer fail, does not count. A strategic answer goes into `open_questions` as `{id, class: 战略, status: answered, quote: "<the user's words>", by: user, at}` (a relayed answer adds `decided_by`, `relayed_by`, `authority`); you write `product-delta.md` and `CHANGELOG.md` rows from what hats return (hats do not edit them), and verified lesson rows to `.sdlc/_lessons.md` (orchestrator-gates §5).

## Step 6 — gates

After each task, run its `workflow.py check-task` presence check and the owning skill’s checks. Only after all participating tasks in a stage have returned, run the stage gate below. In particular, partial-stage tasks use their own checks: designer explore needs no specify artifacts, and architecture feasibility needs no completed spec. Follow stage-procedure for change impact and conformance; a completed report does not settle pending decisions or unverified obligations. Task success never alone adds `shape` or `accept` to `hats_done`.

- **G-script:** the config commands (test / lint / build / migration / e2e) + `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --require --hat <stage> <feature-dir>`. Agent said so ≠ file exists — `ls` first. Plain runs skip with exit 0; `--require` / `--hat` turn a missing file into a failure.
- **G-fresh (L1+):** once per stage after all its producers return (define; shape = designer + architect + dba + invited data hats; implement), plus the final review after accept. The reviewer packet carries artifact paths and the product files named in `product-delta.md` — never your reasoning. Fail (blocker/major unwaived) → producer rework, `current_hat` stays; `review` enters `hats_done` only after the final review passes. L1: the implement G-fresh is the review. Same snapshot, criteria, scope and relevant evidence → reuse `findings.md`; `/sdlc-review` is the report-only entry to the same reviewer.
- **Acceptance (v4):** every participating `accept-*.md` ends with `结论：通过 | 有条件通过 | 不通过`. Any `不通过` → send its gap list to the implement hats (rework on implement, `rework_rounds` +1), then re-run verify and accept.
- **Decisions (v4):** `DECISIONPENDING` is not rework — ask the operator (Step 4). `DEFAULTED` is rework on the producer: the strategic call goes back to 待确认 with options before you ask ([orchestrator-gates.md](references/orchestrator-gates.md) §10).
- **G-self (L3/L4, one pass):** scope, irreversibility, cost, and launch timing vs capacity.
- **Rework with method:** from round 2 the respawn attaches `debug_protocol` and the gate records a one-line `root_cause` ([debug-loop.md](references/debug-loop.md)). Rework ≥ 3 on define or shape is systemic — stop and report.

## Memory = artifacts

Subagents start from files, not your chat. `state.yaml` is the resume map; the product layer is the product's memory; an upstream change marks downstream artifacts `stale` and re-runs the failed gate.

## Metrics

Per feature: acceptance first-pass rate, E2E pass on core journeys, escapes, rework rounds, gate intercepts, spawn count. Judge a gate by risk coverage, escapes, cost and intercepts — zero intercepts alone never justifies removal. Spawn count is a cost to explain, never a reason to skip the designer, dba, growth or acceptance.

## Task scope

Apply [task-scope.md](references/task-scope.md) for project profile, delivery goal and source write boundaries. These scope records do not bypass lane gates.
