---
name: sdlc
description: "Use this skill when the user says /sdlc or continue last SDLC task. Manager window. Do NOT use for $prd-gwt solo or L0. Do not handoff."
when_to_use: "User says /sdlc, follow the process, continue last task, or wants gated swimlanes. Do NOT use for a single-role task ($prd-gwt etc.) or a one-line L0 fix. Do NOT handoff the conversation to a hat."
---

# SDLC orchestrator (manager only) — v4

This window is the **manager** (agents-as-tools): specialists run as nested spawns and you keep the user-facing reply. Do not handoff the conversation to a hat. You classify intent, keep `state.yaml` and the product layer, fill spawn packets, run gates, and run the human decision points. You never write specs, designs, schemas or code (Iron rule 4). Hats load their procedure skills (`prd-gwt`, `design-contract`, `architecture`, `schema`, …) with the Skill tool inside their own context — this window invokes only `sdlc-workflow:discover` / `falsify` in Step 1b.

**What v4 optimizes for:** a product worth using, not artifacts that pass gates. Gates are the hygiene floor. Quality comes from the product layer every hat reads first, diverge-then-converge work with real evidence, experience design before architecture, and acceptance on the running build.

**Slice:** one feature change per `state.yaml`, plus the product layer it reads and writes back (`/sdlc-product` maintains the layer on its own). Not an organizational SDLC: no portfolio intake, vendor/HR/legal process, CI platform or registry ownership, production on-call, multi-repo release trains. Refuse those by quoting this paragraph.

## Entry modes — resolve before Step 0

The command supplies `mode` and arguments; direct skill use defaults to `auto`.
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
6. Experience before architecture: on a UI change the picked design direction exists before the architect starts.
7. Acceptance on the build before the final review: pm walks the journeys, the designer runs design QA, growth checks claims.
8. Strategic decisions belong to the operator. No explicit answer, no decision: stop and wait — never adopt a hat's recommendation as a default.

## References and templates — read when

| File | Read when |
|---|---|
| [references/stage-map.md](references/stage-map.md) | Filling any packet: roles, stages, deliverables, inputs, order, ranks, participation |
| [references/product-layer.md](references/product-layer.md) | Step 0, `product_context` / `product_writes`, `/sdlc-product`, PRODUCTCTX or WRITEBACK failures |
| [references/orchestrator-gates.md](references/orchestrator-gates.md) | A spawn fails, resuming, G-fresh or acceptance fail, rework ≥3, host facts |
| [references/debug-loop.md](references/debug-loop.md) | Rework respawn with `rework_rounds >= 2` |
| [references/ops-vs-sre.md](references/ops-vs-sre.md) | The request says 运营 / 运维 / 增长 / ops / marketing |
| [references/role-agents.md](references/role-agents.md) · [references/subagent-design.md](references/subagent-design.md) | Changing how role prompts are built |
| [templates/sdlc.config.yaml](templates/sdlc.config.yaml) | The project has no config (gates incl. e2e, app start/base_url, product_root) |
| [templates/state.yaml](templates/state.yaml) | Starting or resuming a feature (v4 keys) |
| [templates/product-readme.md](templates/product-readme.md) · [templates/product-changelog.md](templates/product-changelog.md) | Bootstrapping `product_root` |
| [templates/product-delta.md](templates/product-delta.md) | Every v4 feature (writeback record) |
| [templates/spec-s.md](templates/spec-s.md) | L1 / L2-short single-file spec |
| [templates/m/README.md](templates/m/README.md) | L3+ directory layout |
| [templates/role-memory.md](templates/role-memory.md) | Per-role notes under `<feature>/memory/<role>.md` |

## Plugin root

This file is `<plugin>/skills/sdlc/SKILL.md`; **PLUGIN_ROOT** is two directories up (the folder with `skills/`, `agents/`, `commands/`, `scripts/`). Prefer `$ZCODE_PLUGIN_ROOT` when set. Pass the absolute PLUGIN_ROOT in every packet; never hardcode a home path.

## Step 0 — init

1. Read `sdlc.config.yaml` (or copy the template and ask for: constitution, gate commands including `e2e`, `app.start` / `app.base_url`, `product_root`). Run `python3 <PLUGIN_ROOT>/scripts/check_config.py --project-root <root>`: blockers go to the user with the suggested block (you never write their config), and no UI stage starts until the app can run ([orchestrator-gates.md](references/orchestrator-gates.md) §12).
2. **Product layer:** resolve `product_root` (default `docs/product`). Copy missing templates per [product-layer.md](references/product-layer.md) — never overwrite. A new feature's `state.yaml` gets `sdlc_version: 4` and `product_root`. If the layer is mostly unfilled and the product already exists, recommend `/sdlc-product` before the first feature.
3. **Resume:** an unfinished `<artifact_root>/.sdlc/*/state.yaml` → class `resume`. Normalize legacy Chinese hat words once. Last fresh-context `fail` → stay on the producing hat (HATADVANCE).
4. Note whether `sdlc-workflow:<role>` types exist in the host spawn table; if not, use the `host_spawn` fallback ([orchestrator-gates.md](references/orchestrator-gates.md) §1).

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
| `discovery` | "先调研/先讨论", or L2+ new feature with no briefing | Step 1b |
| `new-feature` | gated delivery and briefing `done`/`skipped` | Step 2 |

Single-hat discipline: do not invoke `$prd-gwt` or any procedure skill here; do not inflate a single-hat request into a lane. "Also review it" → `/sdlc-review` after files land.

## Step 1b — discover (before lane, before pm)

When class is `discovery`, or `new-feature` at L2+ without `discovery.status: done|skipped|killed`: invoke `sdlc-workflow:discover` in this window and follow it — Frame → market ∥ compete → **growth** → Discuss-P → Discuss-S → Falsify → freeze `00-discover/briefing.md`. No pm, architect or implement spawns in this step; no `spec.md`. Skip predicates (closed set): (a) briefing on disk and the user says continue; (b) explicit skip and a spec exists; (c) you will judge L1. Verdict `killed` → stop. After the freeze and the human's go → Step 2.

## Step 2 — lane and participation

Lane questions: **Q1** schema? **Q2** auth/tenant? **Q3** external contract? **Q4** irreversible? **Q5** new dependency? **Q6** files > threshold (default 20) or 2+ subprojects? Participation questions, recorded in state: **Q-ui** user-facing UI → `ui: yes|no`; **Q-tracking** new or changed events/metrics → `tracking: yes|no`. `q_security: yes` when Q2, Q3 or Q4.

Lane completion requirements are generated in [references/stage-map.md](references/stage-map.md). Apply participation and ordering from [references/stage-procedure.md](references/stage-procedure.md); selecting a lane does not dispatch every available agent. A skipped role needs a reason and does not remove aggregate stage requirements.

**L2-short predicate (closed set) — skips only the architect:** (a) `intent.skip_shape: true` and `02-shape/contract.md` already on disk; or (b) the implement packet marks the contract `required: false` and names `spec.md` as its substitute. `path: short` or appetite < 4h alone is not enough.

## Step 3 — spawn packet v2 (the only spawn form)

```
## SPAWN PACKET v2
hat: <spawn_role>
stage: <stage-id from stage-map.md>
task: <explore|specify|walkthrough|design-qa|claims-check|positioning|launch|T-n|…>
subagent_type: sdlc-workflow:<spawn_role>
intent_quote: "<user's last substantive message, ≤200 chars>"
lane: L1|L2|L3|L4
feature_dir: <abs>
PLUGIN_ROOT: <abs>
constitution: <abs or none>
product_root: <abs>
product_context:            # read first — defaults in product-layer.md
  - <abs>
product_writes:             # files this hat owns and must keep true; empty for reviewer/qc
  - <abs>
lane_file: <ui|api|ai|model|none>
slice_integrator: <one implementation role, required for implement tasks>
primary_skill: sdlc-workflow:<proc>
companion_skills: []        # only what the contract lists: tdd | refactor (implement) · collect (pm when tracking: yes); prototype is for discovery only
inputs:                     # files the hat must read — never directories
  - {path: <abs>, required: true|false}
explore_roots:              # directories it may search with Grep/Glob, not read wholesale
  - <abs>
deliverable_paths:
  - <relative to feature_dir>   # implement: 03-impl/T-<n>-<role>-evidence.md (one file per lane)
evidence_required:          # copy the contract's `evidence` list (web | screenshots | running_app | e2e); add, never drop
  - <kind>
visuals: []                 # diagrams this task draws (contract `visuals`; trust-boundary is required when q_security: yes).
                            # Non-empty → add contract.diagram.inputs to inputs, contract.diagram.deliverable to
                            # deliverable_paths and contract.diagram.check to success_checks. A diagram is a view of its
                            # source: draw it only when it removes ambiguity for the next hat.
forbidden:
  - Do not spawn further subagents (host depth 1).
  - Do not invoke procedure skills beyond primary_skill and companion_skills (reviewer/qc may load any to judge; debug_protocol adds sdlc-workflow:debug).
  - Do not Write outside deliverable_paths and product_writes (reviewer/qc: do not Write at all).
  - Do not read <feature>/memory/*.md unless it is your own memory_file.
memory_file: <abs or empty>
debug_protocol: <abs or empty>
success_checks:
  - each deliverable_paths exists on disk
  - <the contract's success_check with the real paths filled in>
return: output paths + summary + decisions + open_questions (strategic → Q-* 待确认 + options + recommendation; operational → default applied) + product-delta rows
```

**Scale the deliverable, never the evidence.** A packet never waives web research, screenshots, the running app or E2E — no "smoke run: no WebSearch needed", no "URLs optional", no "fall back to reading source code". To save cost, ask for a shorter artifact. Save every packet to `<feature>/packets/<nn>-<stage>-<hat>.md` and run `python3 <PLUGIN_ROOT>/scripts/check_packet.py <file>` before spawning. It rejects waivers like these, a missing or mismatched check-task line (`workflow.py contract` prints the exact `success_check`), an `evidence_required` list shorter than the contract's `evidence`, deliverables outside the feature directory, directory inputs, oversized `product_context`, writes to files a hat does not own (including `product-delta.md` and `CHANGELOG.md`, which only you write), and `--hat <role>`. Errors → fix the packet; never spawn around them.

`subagent_type` is always the qualified name. Unknown type → one `general-purpose` fallback that Reads `PLUGIN_ROOT/agents/<role>.md` and the primary SKILL.md; record `host_spawn`. Native and fallback both succeeding for one hat is a dual-dispatch defect. Reviewer and qc: no `memory_file`, no `product_writes`; write their deliverable from the final message before any other spawn. For qc you run `skills/coverage-matrix/scripts/check-matrix.py` and paste its output into the packet. `mcp_adapters` in the config is a warning list only.

## Step 4 — human decision points (you present, the human decides)

- **Discovery freeze** (Step 1b).
- **Design direction pick** (`ui: yes`): after designer `explore`, show each direction in one line — signature moment, trade-off, screenshot paths — plus the designer's recommendation, and wait. Record `design: {picked: D<n>, picked_by: user|delegated, at}`. The designer's `specify` spawn writes `选定：D<n>` into `design-directions.md`.
- **Strategic decisions** (`Q-*` rows with 类别 战略, 状态 待确认): ask all of them in one round — question, options, the hat's recommendation — and **wait**. Only an explicit answer counts. Silence, a question tool that returns no answer, or a question the user never saw is not consent. "按推荐" or "你定" from the user is an answer; record it as such. Record each answer in `open_questions` (Step 5) and respawn the owner to write 已确认 with the operator's words. No answer → the dependent stage does not start: `phase: Stopped`, reason `waiting-for-operator`, and tell the user what is waiting.
- **Operational defaults** (状态 默认): list them in your report; the user can overturn any of them later.
- **Acceptance** verdict `有条件通过`: the user accepts the conditions or sends the slice back. Record acceptance as `open_questions` entry `{id: Q-ACCEPT-<PM|DESIGN|GROWTH>, status: answered, by: user, quote: "<their words>"}`; the gate checks it.

## Step 5 — state.yaml

Update after every hat. `current_hat` / `hats_done` use English words from the stage map. `phase` holds only the persistent enum (`Intent|Discovering|LaneJudge|HatReady|Spawned|Rework|HatDone|Closed|Stopped|Refused|L0done`). v4 keys: `sdlc_version: 4`, `product_root`, `ui`, `tracking`, `design`, `discovery.tracks.growth`. Gate kinds: `script | fresh-context | self-review`; `result: null` needs `reason`. Run E2E through `python3 <PLUGIN_ROOT>/scripts/evidence.py run --feature <feature_dir> --name e2e -- <e2e command>` and paste the gate record it prints (with `evidence:`); a pass without a current run record, or an older pass after a newer fail, does not count. A strategic answer goes into `open_questions` as `{id, class: 战略, status: answered, quote: "<the user's words>", by: user, at}`; you write `product-delta.md` and `CHANGELOG.md` rows from what hats return (hats do not edit them).

## Step 6 — gates

After each task, run its `workflow.py check-task` presence check and the owning skill’s checks. Only after all participating tasks in a stage have returned, run the stage gate below. In particular, designer explore does not require a picked direction or specify artifacts. Task success never alone adds `shape` or `accept` to `hats_done`.

- **G-script:** the config commands (test / lint / build / migration / e2e) + `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --require --hat <stage> <feature-dir>`. Agent said so ≠ file exists — `ls` first. Plain runs skip with exit 0; `--require` / `--hat` turn a missing file into a failure.
- **G-fresh (L1+):** once per stage after all its producers return (define; shape = designer + architect + dba + invited data hats; implement), plus the final review after accept. The reviewer packet carries artifact paths and the product files named in `product-delta.md` — never your reasoning. Fail (blocker/major unwaived) → producer rework, `current_hat` stays; `review` enters `hats_done` only after the final review passes. L1: the implement G-fresh is the review. Same snapshot (sha256) → reuse `findings.md`; `/sdlc-review` is the report-only entry to the same reviewer.
- **Acceptance (v4):** every participating `accept-*.md` ends with `结论：通过 | 有条件通过 | 不通过`. Any `不通过` → send its gap list to the implement hats (rework on implement, `rework_rounds` +1), then re-run verify and accept.
- **Decisions (v4):** `DECISIONPENDING` is not rework — ask the operator (Step 4). `DEFAULTED` is rework on the producer: the strategic call goes back to 待确认 with options before you ask ([orchestrator-gates.md](references/orchestrator-gates.md) §10).
- **G-self (L3/L4, one pass):** scope, irreversibility, cost, and launch timing vs capacity.
- **Rework with method:** from round 2 the respawn attaches `debug_protocol` and the gate records a one-line `root_cause` ([debug-loop.md](references/debug-loop.md)). Rework ≥ 3 on define or shape is systemic — stop and report.

## Memory = artifacts

Subagents start from files, not your chat. `state.yaml` is the resume map; the product layer is the product's memory; an upstream change marks downstream artifacts `stale` and re-runs the failed gate.

## Metrics

Per feature: acceptance first-pass rate, E2E pass on core journeys, escapes after release, rework rounds, gate intercepts, spawn count. A gate that never intercepts should be removed from config. Spawn count is a cost to explain — never a reason to skip the designer, dba, growth or acceptance.
