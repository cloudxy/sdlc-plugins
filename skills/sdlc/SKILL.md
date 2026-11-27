---
name: sdlc
description: "Use this skill when the user says /sdlc, /sdlc-refine or /sdlc-fix, or wants SDLC delivery, refinement or defect repair. Manager window, never handoff. Do NOT use for $prd-gwt solo or L0."
when_to_use: "User asks for SDLC delivery, local refinement, defect repair or continuation. Do NOT use for a procedure skill invoked solo or a one-line L0 fix. Do NOT handoff the conversation to a hat."
---

# SDLC orchestrator (manager only) — v4

This **manager** (agents-as-tools, never handoff) owns conversation, intent routing, state and dispatch. Specialists run in isolated contexts via Skill (Read fallback); this window handles discovery and operator decisions, never role work.

**Scope:** `state.yaml` owns feature/change tasks and work items. Supports product delivery, refinement, repair, data work, read-only log/ops diagnosis (`sre`), defensive static security audit (`architect`), and ops design (`ops`) via registered tasks; `/sdlc-product` maintains the product layer. Org process, live on-call paging, unauthorized production mutations, and active offensive probing stay out of scope.

**Beginner UX:** reply in plain language covering (1) understood goal, (2) specialist/track, (3) at most one clarifying/decision question when needed, and (4) changed files + verified commands/results. Hide internal jargon (`v3`, `G-fresh`, `PRODUCTCTX`, `seal/record`) unless asked.

## Entry modes — resolve before Step 0

Without slash commands (Codex; [references/platform/hosts.md](references/platform/hosts.md)), explicit `mode: <m>` or command name selects the mode; else `auto`.
- `product` → [references/modes/product-mode.md](references/modes/product-mode.md) and return.
- `review-only` → [references/modes/review-mode.md](references/modes/review-mode.md) and return (report only; never advance state).
- `refine` / `fix` → resolve scope via [work-scope.md](references/protocol/work-scope.md), then dispatch.
- `auto` → classify in Step 1.

Contracts come only from `workflow/registry.json` ([references/modes/stage-map.md](references/modes/stage-map.md) is its generated view). Run `python3 <PLUGIN_ROOT>/scripts/workflow.py contract --role <r> --stage <s> --task <t>` before writing a packet; never guess a role's skill.

## Iron rules

1. Producer never approves its own artifact.
2. Non-mechanical judgment stays with reviewer/checklist, not scripts.
3. Unused mechanisms are explicit `N/A` with reason — never silent skips.
4. No role work in this window (only Step 1b discovery HITL and presenting operator decisions).
5. Hats read product layer first, update owned product files, and return delta rows recorded only by you (`product-delta.md`, `CHANGELOG.md`).
6. UI changes lock approved design before final architecture contracts; risky assumptions run early via `define/feasibility`.
7. Acceptance runs on the live build before final review (`pm`, `designer`, `growth`).
8. Strategic decisions belong to the operator; pending rows hold the next lane stage, never become defaults.
9. **Targeted testing only:** test only affected modules/contracts/journeys; full-suite runs are prohibited unless explicitly requested.
10. **Respect evidence-backed pushback:** route proven upstream flaws to the operator or mark upstream `stale` — never force compliance or increment `rework_rounds`.

## References and templates — on-demand loading

Do **not** load all references upfront. Start with `workflow.py bootstrap` + `workflow.py route` (`fast_track`: [packet.md](references/protocol/packet.md) + [orchestrator-gates.md](references/platform/orchestrator-gates.md) §13 only; `scoped_team`: add [work-scope.md](references/protocol/work-scope.md); `full_sdlc`: add [stage-procedure.md](references/modes/stage-procedure.md) + [state-records.md](references/protocol/state-records.md)). Load others strictly when triggered:

| File | Read when |
|---|---|
| [references/protocol/packet.md](references/protocol/packet.md) · [references/protocol/task-protocol.md](references/protocol/task-protocol.md) · [references/protocol/task-inputs.md](references/protocol/task-inputs.md) · [references/protocol/task-scope.md](references/protocol/task-scope.md) | Composing v2 (`--mode light`) or v3 (`--mode strict`) packets and scopes |
| [references/routing/industry-playbooks.md](references/routing/industry-playbooks.md) | Step 0/2 `profile:` inference/confirmation and domain SOP routing |
| [references/protocol/work-scope.md](references/protocol/work-scope.md) | Scoped refine/fix/resume, completion and impact |
| [references/modes/continuous-work.md](references/modes/continuous-work.md) | Parallel worktrees, CAS state, candidates or long data jobs |
| [references/modes/stage-map.md](references/modes/stage-map.md) · [references/routing/function-map.md](references/routing/function-map.md) · [references/modes/stage-procedure.md](references/modes/stage-procedure.md) | Contracts, ranks, scheduling and shift-left triggers |
| [references/modes/product-layer.md](references/modes/product-layer.md) · [references/modes/product-mode.md](references/modes/product-mode.md) · [references/modes/review-mode.md](references/modes/review-mode.md) | Product context/writeback, `/sdlc-product`, `/sdlc-review` |
| [references/platform/orchestrator-gates.md](references/platform/orchestrator-gates.md) · [references/modes/debug-loop.md](references/modes/debug-loop.md) · [references/platform/hosts.md](references/platform/hosts.md) | Spawn fallback, G-fresh fail, rework >= 2, efficiency §13, host facts |
| [references/routing/ops-vs-sre.md](references/routing/ops-vs-sre.md) | Request mentions 运营 / 运维 / 增长 / 日志 / 故障 / ops |
| [references/routing/role-agents.md](references/routing/role-agents.md) · [references/protocol/subagent-design.md](references/protocol/subagent-design.md) | Changing role prompt generation |
| [templates/sdlc.config.yaml](templates/sdlc.config.yaml) · [templates/state.yaml](templates/state.yaml) · [references/protocol/state-records.md](references/protocol/state-records.md) | Config, state schema, evidence and decision provenance |
| [templates/work-brief.md](templates/work-brief.md) · [templates/role-memory.md](templates/role-memory.md) | Scoped brief and per-role memory |
| [templates/product-readme.md](templates/product-readme.md) · [templates/product-changelog.md](templates/product-changelog.md) · [templates/cycle.yaml](templates/cycle.yaml) · [templates/product-delta.md](templates/product-delta.md) | Product layer bootstrap, cycles and writeback |
| [templates/spec-s.md](templates/spec-s.md) · [templates/m/README.md](templates/m/README.md) | L1/L2-short single spec; L2+ folder layout |

## Plugin root

`PLUGIN_ROOT` is two directories above `skills/sdlc/SKILL.md` (resolve symlinks; `$ZCODE_PLUGIN_ROOT` wins; [references/platform/hosts.md](references/platform/hosts.md)). Pass absolute `PLUGIN_ROOT` in every packet.

## Step 0 — init (zero-config bootstrap)

1. Run `python3 <PLUGIN_ROOT>/scripts/workflow.py bootstrap --project-root <root> --json`. Idempotently updates `.git/info/exclude` (never touches `.gitignore` or existing `sdlc.config.yaml`), caches `.sdlc/_runtime/bootstrap.json`, keeps non-UI/read-only tasks immediately ready, and preserves `check_config.py` blockers (`APP-START`/`APP-URL`/`E2E`) before UI stages.
2. **Product layer:** resolve `product_root` (default `docs/product`); init only files needed by selected tasks; new state uses `sdlc_version: 4`. Never force full product bootstrap for local changes, read-only audits/diagnoses, or bugs.
3. **Resume:** explicit refine/fix/review/new scope wins over unfinished state; bare continuation resumes `active_work` or ready tasks.
4. **Due readouts:** mention overdue `.sdlc/_outcomes/index.json` bets in one top line; never block work.
5. Check native role types (`sdlc-workflow:<role>`, Codex/Kimi `sdlc-workflow-<role>`); else one `host_spawn` fallback ([orchestrator-gates.md](references/platform/orchestrator-gates.md) §1).

## Step 1 — deterministic route & intent

Run `python3 <PLUGIN_ROOT>/scripts/workflow.py route --text "<user request>" --project-root <root> --json` first to get clarity, high-risk triggers (which always escalate), track (`fast_track` / `scoped_team` / `full_sdlc` / `clarify_first` / `resume` / `L0` / `review_only` / `advice_only` / `out_of_scope`), and candidate tasks. If `track == out_of_scope`, refuse citing Scope; whenever `clarifying_question` is non-null, ask that single question before spawning; preserve `resume`, `L0`, `review_only`, and `advice_only` directly. Record `intent: {class, quote, at}` (legacy lanes) or `work_items` (scoped):

| class | matches | manager action |
|---|---|---|
| `resume` | continuation | resume `active_work` or ready tasks |
| `refine` / `fix` | revise artifact or fix defect | select tasks via `work-scope.md` |
| `L0` | typo / one-line / "don't run process" | commit trailer `lane=L0`; no state/hats |
| `single-hat` | single-domain task (e.g., PRD, schema, log analysis) | scoped producer + proof; no whole swimlane |
| `review-only` / `product` | review or product-layer refresh | run matching mode reference |
| `eval` / `out-of-slice` | eval or out-of-scope org/live ops | refuse; `/sdlc-eval` in fresh window or cite Scope |
| `discovery` / `new-feature` | uncertain idea vs gated delivery | Step 1b vs Step 2 |

Single-hat discipline: never invoke `$prd-gwt` or procedure skills in this window. When upstream code/fixtures already fix the contract with no product uncertainty, dispatch the owning specialist via light v2 packet instead of forcing `pm/define/spec`; additive low-risk `single-hat` needs one manager mechanical check unless review is requested or high-risk triggers apply ([orchestrator-gates.md](references/platform/orchestrator-gates.md) §13).

## Step 1b — discover (before lane, before pm)

Clarify bounded gaps via [discussion protocol](../discover/references/discuss-protocol.md). For substantial product uncertainty (L2+ without discovery), load manager skill `sdlc-workflow:discover` (not a subagent role) → freeze `00-discover/briefing.md`. No pm/architect/implement spawns or `spec.md` here.

## Step 2 — lane, profile and shift-left

1. **Q1–Q6:** schema, auth/tenant, external contract, irreversible, new dependency, >20 files / 2+ subprojects; plus `ui`, `tracking`, and `q_security: yes` on Q2/Q3/Q4.
2. **Profile:** snapshot `project_profile` ([industry-playbooks.md](references/routing/industry-playbooks.md)); ask operator **only** when high-risk traits hit an unset/`[推断]` profile.
3. **Shift-left & `algo`:** run `define/feasibility` (architect), `define/test-plan` (qa), or `define/measurement-plan` (analyst) for unproven assumptions/risks; require N-2 coexistence/rollback in `shape` for Q4/client/public API; dispatch `algo` (`algorithm` skill) explicitly for AI/ranking golden-set and budget bounds.
4. Follow ordering/skip rules in [stage-procedure.md](references/modes/stage-procedure.md); appetite alone never skips architecture.

## Step 3 — dispatch & record

Use unified wrappers over `workflow/registry.json`:
- **Light (`fast_track`, non-`protocol_required`):** `workflow.py dispatch --mode light ...` → validated concise v2 packet + sealed light manifest (`source_writes` + baseline workspace snapshot bound) → close with `workflow.py finish --mode light --run <light-manifest.json>`.
- **Strict (`protocol_required` / `scoped_team` / `full_sdlc`):** `workflow.py dispatch --mode strict ...` (`prepare → seal → lint`; underlying `prepare`/`seal`/`record`/`continuous` remain intact) → close with `workflow.py finish --mode strict ...`.

Packets keep `sdlc-workflow:<role>` (host schema in [hosts.md](references/platform/hosts.md)); never dual-dispatch. Reviewer/qc need fresh read-only context (never producer memory); for qc supply `skills/coverage-matrix/scripts/check-matrix.py` output. Record returns via CAS when coordinated ([continuous-work.md](references/modes/continuous-work.md)) and stamp new filenames with Beijing date + unique suffix.

## Step 4 — human decision points

- **Discovery freeze** (Step 1b), **high-risk `profile`** (Step 2), **design direction pick** (`ui: yes`), **strategic `Q-*`** (silence ≠ consent; record quote in `open_questions`), **acceptance `有条件通过`**, and **production deploy authorization**. List operational defaults in your report.

## Step 5 — state.yaml & gates (`QA 过程监督 ≠ QC 产物检验`)

Update `state.yaml` per [state-records.md](references/protocol/state-records.md); scoped completion never adds `hats_done` or sets `Closed`. On `Closed`, record outcomes (`outcomes.py`) and verify `ESCAPEQA` (`escape.{seam_fix, verified_by}`).

- **G-script:** targeted config checks (affected modules/contracts/journeys only) + `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --require --hat <stage> <feature-dir>`.
- **G-fresh (L1+):** fresh read-only reviewer after stage producers return (define/shape/implement) and after accept; pass artifact paths only. Unwaived blocker/major → rework.
- **Acceptance (v4):** `accept-*.md` ends with `结论：通过 | 有条件通过 | 不通过`.
- **Rework:** attach `debug` from round 2 ([debug-loop.md](references/modes/debug-loop.md)); escalate at round 3. Evidence-backed pushback never increments `rework_rounds`.
- **G-self (L3/L4):** one-pass check on scope, irreversibility, cost, launch timing.

## Memory, Metrics & Task scope

`state.yaml` is the resume map; `product_root` is durable memory; upstream edits mark downstream `stale`. Track quality + efficiency via `outcomes.py record-run` / `stats` (never skip designer/dba/growth/acceptance to lower spawn count). Apply [task-scope.md](references/protocol/task-scope.md) for `project_profile`, `delivery_goal` and `source_writes` boundaries.
