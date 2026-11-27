---
name: impl-evidence
description: "Use this skill when the spawn packet sets lane_file=ui|api|ai|model. Do NOT load in /sdlc or to design schema."
when_to_use: "Use this skill when the spawn packet sets lane_file=ui|api|ai|model. Load inside sdlc-workflow:frontend / backend / algo / miner. Do NOT use from parent /sdlc. Do NOT use to design schema or GWT."
---

# Implementation evidence — contract in, command+exit out

Shared implementer procedure. Identity stays with `sdlc-workflow:frontend` / `backend` / `algo` / `miner`. The spawn packet's **`lane_file`** field selects your lane.

**Orient rule 1 (before anything else):** read `lane_file` from the spawn packet.

- `lane_file` missing, empty, or not one of `ui|api|ai|model` → **stop**. Do not read any lane file. Return to the orchestrator: "packet has no valid lane_file".
- Otherwise read **only** `references/<lane_file>.md`, `references/<lane_file>/`, and the matching domain archetype in [references/industry-delivery-sops.md](references/industry-delivery-sops.md) (aligned with [industry-architecture-sops.md](../architecture/references/industry-architecture-sops.md) and [industry-data-sops.md](../schema/references/industry-data-sops.md)). Read another lane only when a concrete interface dependency requires it; reading never grants that role's write authority.

Job: **implement a journey slice or scoped experiment/repair that works end-to-end at its consumer boundary, obeying foundational engineering laws, and leave replayable verbatim evidence.** Contract in; targeted command + exit code out; for UI slices, runtime screenshots against the real backend visually compared against the final prototype. Never drift GWT, schema, or design tokens.

**Read the why first:** the ticket's journey `J-n`, spec §2 (core value, signature moment), final prototype code/version + `data-component` IDs + state routes + `design-system.md` (UI), `schema.dbml` + `db-spec.md` (data), and `tracking.md` (when events change).

| Hat | Lane file (packet `lane_file`) | Registered Lifecycle Tasks |
|---|---|---|
| `frontend` | `ui` → [ui.md](references/ui.md) then `references/ui/` | `implement/T-<n>`, `implement/diagnose`, `implement/fix` |
| `backend` | `api` → [api.md](references/api.md) then `references/api/` | `implement/T-<n>`, `implement/diagnose`, `implement/fix` |
| `algo` | `ai` → [ai.md](references/ai.md) then `references/ai/` | `implement/T-<n>`, `implement/explore`, `implement/evaluate`, `implement/diagnose`, `implement/fix` |
| `miner` | `model` → [model.md](references/model.md) then `references/model/` | `implement/T-<n>`, `implement/explore`, `implement/experiment`, `implement/evaluate` |

## Scoped exploration, diagnosis, repair and revalidation

- **Miner `implement/explore | experiment | evaluate`** (`lane_file: model`): independent data/modeling investigation with a business action question, pinned dataset snapshot ID (never `"latest partition"`), dual-timestamp `(entity, availability_time <= decision_time)` feature discipline, idempotent byte-identical overlapping-window backfills, fail-closed feature contracts, deployment-matched temporal/group splits, rules baseline, 5-anchor reproducibility lock, pre-registered offline→online experiment metrics (`1` primary + `≤ 3` secondary/guardrail + stopping rule), and PSI/KS train-serve parity (`03-impl/mining-<task>-evidence.md`). `explore` can establish the evaluation plan; `experiment`/`evaluate` require an accepted plan. Downstream segments/scores are proposed to `data-warehouse-engineer` for `data/tags.yaml` registration — `miner` never edits `data/tags.yaml` directly.
- **Algo `implement/explore | evaluate`** (`lane_file: ai`): independent AI/RAG/Agent capability exploration or frozen-split benchmark (`03-impl/ai-<task>-evidence.md` or packet `deliverable_paths`). Lock 5 reproducibility anchors (seed, dependency lockfile, pinned `eval-set-v<n>` snapshot ID, config SHA-256, runtime digest) and pre-register offline gate floors + online A/B or interleaving rules (`1` primary + `≤ 3` secondary/guardrail metrics + stopping rule before launch). `explore` frames task failure cost, builds/validates a stratified `eval-set-v<n>`, and establishes rules baseline + ceiling; `evaluate` compares candidates one variable at a time on the identical frozen `eval-set-v<n>` with cost/latency/token bounds. Production integration remains a separately scheduled slice.
- **Independent `implement/diagnose`** (`frontend`, `backend`, `algo` with `debug`): read-only reproduction and mechanism isolation written to `04-verify/diagnosis-<role>.md` — zero unauthorized production source edits.
- **Scoped `implement/fix`** (`frontend`, `backend`, `algo`): consumes a reproducible defect, accepted behavior/eval and technical baselines (a narrow owner-decision baseline is valid without rebuilding historical PRDs), and authorized `source_writes`. Keep baselines read-only, attach `debug`, fix the minimal mechanism, run targeted reproduction + regression/eval checks, and write `03-impl/fix-<role>-evidence.md` (plus `03-impl/fix-integration.md` for the assigned integrator).
- **Revalidation**: inspect unchanged code and rerun affected targeted checks against updated inputs; never rewrite code merely to fabricate a fresh diff.

## High-order engineering discipline & gotchas

- **Foundational principles in code**: **Parse, Don't Validate** untrusted inputs once at the boundary into narrow types/Branded IDs and **discriminated unions** (no conflicting boolean flag soup); isolate complex deterministic logic in a pure **Functional Core** behind a thin I/O shell; enforce **ISP/DIP/LoD** (no ORM leaks or `a.b.c.d()` cross-aggregate reaching); enforce **DIE/SSOT** on shared visibility predicates, limits, error codes, and tokens while avoiding premature boolean-flag helpers across diverging actors (**AHA**).
- **Contract-driven Backend & Frontend seam exit criteria**: `backend` implements 100% of LLD error classifications returning exact contract `code`s, runs **executable contract tests** verifying response shape/status/nullability before `qa` handoff, and implements LLD retry/circuit-breaker/fallback paths OR explicitly records `本次不实现（原因+授权）` in `impl-evidence.md` (zero silent omissions). `frontend` generates TypeScript types & mocks directly from the locked contract to build in parallel, demonstrating **all 7 component interactive states (`default, hover/focus, disabled, loading, empty, error, success`) × applicable screen states**, zero-`TBD` microcopy, and generated-type compile (`tsc --noEmit` / build `exit: 0`) so slice integration handles only real business state.
- **Strict CQS & Process Statelessness**: `GET`/preview/probe endpoints must have zero side effects or billing consumption. Backend processes must remain **100% stateless across horizontal workers** — never store mutable session, progress, rate-limit, permission cache, or cross-request lock state (`RLock` / `asyncio.Lock`) in module globals, `dict`s, or uncoordinated local tempfiles.
- **Bounded Everything & Three-State Effects (`Success / Fail / In-Doubt`)**: bound every query, batch, timeout, retry (with jitter), and AI token/step loop; keep external HTTP/MQ/LLM calls outside DB transactions; treat write read-timeouts as `In-Doubt` (check upstream receipt / replay exact idempotency key before retry).
- **DBA vs Backend Migration Ownership**: destructive DDL, `expand-contract`, backfills, and shared-table changes belong **exclusively to `dba` (`dba/migration`)**; routine additive slice-local tables in `backend` must match approved `schema.dbml` + ORM metadata + package manifest 1:1 with verbatim parity checks ([references/industry-delivery-sops.md](references/industry-delivery-sops.md)). Escalate any missing schema/contract/GWT item to `dba` / `architect` / `pm`.
- **Targeted tests only — full-suite test runs are prohibited.** Run only the unit, parity, eval, concurrency, and consumer-integration checks covering the ticket's touched files, contracts, and callers.
- **Tests green ≠ slice works.** One per-role evidence file (`03-impl/T-<n>-<role>-evidence.md` via [templates/impl-evidence.md](templates/impl-evidence.md)), plus `03-impl/T-<n>-integration.md` ([templates/integration.md](templates/integration.md)) from `slice_integrator` against the real consumer surface (for UI: real backend + `bash PLUGIN_ROOT/scripts/ui-evidence.sh <url> 03-impl/screens/T-<n> 375,1440` visually compared with the final prototype + `tracking.md` events verified).
- **Companion procedures (`tdd`, `refactor`, `debug`)**: fulfill `required_companion_skills` (or report unavailable); record TDD expected pre-impl Red runs inside `### TDD Red -> Green` separate from final `exit: 0` verification commands; append `## Debug record` on `debug_protocol` respawns.

## Shared self-check

- [ ] Packet `lane_file` valid (`ui|api|ai|model`); source edits strictly inside authorized `source_writes`?
- [ ] Parse-at-boundary, discriminated unions, DIE/SSOT, CQS, Process Statelessness, Bounded/Three-State rules, and industry archetype obligations ([references/industry-delivery-sops.md](references/industry-delivery-sops.md)) satisfied?
- [ ] Lane seam gates met (`backend`: 100% LLD error `code`s + executable contract tests + resilience or `本次不实现（原因+授权）`; `frontend`: contract-generated TS types/mocks + `tsc --noEmit` + 7 interactive states × screen states + zero-`TBD` copy; `miner`/`algo`: `availability_time <= decision_time`, fail-closed feature contracts, PSI/KS parity, 5-anchor reproducibility & pre-registered metrics)?
- [ ] Evidence uses lean lane-adaptive [templates/impl-evidence.md](templates/impl-evidence.md) with **targeted** verbatim commands + `exit: 0`?
- [ ] Real consumer integration recorded in `T-<n>-integration.md` (with inspected prototype-compared screenshots for UI) and `tracking.md` events verified?
- [ ] Zero silent drift on GWT, `schema.dbml`, tokens, or `data/tags.yaml` ownership?

## References, templates and scripts — load only when applicable

| File | Use when |
|---|---|
| [references/industry-delivery-sops.md](references/industry-delivery-sops.md) | DBA/Backend migration boundary, Miner→Warehouse tag handoff, and 9 industry archetype proofs |
| [references/backend-task.md](references/backend-task.md) | Backend protocol-1 ticket: pinned inputs, scope, consumer evidence and structured return |
| [references/local-media.md](references/local-media.md) | Slice requires local/offline media replication, byte digests, staging safety, or Range playback |
| [references/client-platforms.md](references/client-platforms.md) | Slice targets native mobile (iOS/Android), desktop shell (Electron/Tauri), or mini-program |
| [templates/impl-evidence.md](templates/impl-evidence.md) · [templates/integration.md](templates/integration.md) | Lean lane-adaptive per-role evidence and slice consumer integration record |
| [templates/task-spec.md](templates/task-spec.md) · [templates/eval-set.md](templates/eval-set.md) · [templates/model-choice.md](templates/model-choice.md) | `algo` task framing, versioned 5-layer eval set, and baseline/fallback ladder |
| [templates/problem-framing.md](templates/problem-framing.md) · [templates/feature-dict.md](templates/feature-dict.md) · [templates/model-card.md](templates/model-card.md) | `miner` action-first framing, `< :asof` feature dictionary, and model card + tag proposal |
| `scripts/check-layering.py` · `scripts/check-frontend.py` | Mechanical Router/ORM boundary check (`backend`) and token/hardcode check (`frontend`) |

## Role-specific review

Apply [references/role-quality.md](references/role-quality.md) ("Expert Bar vs Mediocre Order-Taker + Second-Order Scan") alongside this procedure's self-check.
