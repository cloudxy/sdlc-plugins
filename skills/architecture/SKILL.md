---
name: "architecture"
description: "Use when assessing feasibility, boundaries, quality/security, contracts or conformance. In architect or $architecture. Do NOT use for production code or schemas."
when_to_use: "Use for architecture baselines, feasibility, contracts, change impact or conformance. Do NOT run as the /sdlc manager or replace PM, DBA, implementation or release approval."
---

# Architecture — business goals to verifiable system decisions

Job: **turn business goals into the smallest actionable architecture change, with evidence, clear ownership and verifiable obligations.** Reuse a valid decision when it still fits; compare alternatives when there is a real unresolved choice. A diagram communicates a decision; it does not prove feasibility.

## Select the task

Task names, output paths and ownership have one source: `workflow/registry.json`. Scheduling belongs to the manager; task procedures and baseline state transitions belong to [lifecycle.md](references/lifecycle.md).

| Task | Purpose & Canonical Deliverable |
|---|---|
| product / bootstrap | Establish or refresh an evidence-backed baseline ([templates/architecture-baseline.md](templates/architecture-baseline.md)) |
| define / feasibility | Test a risky assumption before PM/design freezes dependent choices ([templates/architecture-feasibility.md](templates/architecture-feasibility.md)) |
| shape / contract | Turn approved scope and design into deep boundaries, contracts and executable slices ([templates/contract.md](templates/contract.md), [templates/api-contract.md](templates/api-contract.md), [templates/adr.md](templates/adr.md), [templates/story.md](templates/story.md)) |
| shape / security-review | Conditional. When selected (`q_security: yes`, or touching auth/session/tenant isolation, PII retention/consent, external dependency/vendor lock, or agent/IPC boundaries), record only that delta per [threat-model.md](references/threat-model.md) ([templates/security-review.md](templates/security-review.md)) |
| verify / security-audit | Standalone **defensive static** security audit of existing code/config/dependencies (`04-verify/security-audit.md`) per [threat-model.md](references/threat-model.md) (STRIDE/trust-boundary & least-privilege review); run `python3 <PLUGIN_ROOT>/scripts/tools/sec_quickscan.py <path>` as static clues then perform semantic review. **Strictly defensive static only — zero active probing, exploitation, or attack automation** |
| shape / change-impact | Assess a discovered mismatch; route decisions and invalidate affected artifacts ([templates/architecture-change-impact.md](templates/architecture-change-impact.md)) |
| verify / conformance | Use [conformance-task.md](references/conformance-task.md) to compare accepted obligations with actual implementation and checks ([templates/architecture-conformance.md](templates/architecture-conformance.md)) |
| cycle / deepen-survey | In a product cycle, use [deepening.md](references/deepening.md) to list hot-spot deepening candidates for a person to choose; no refactor |

These are conditional tasks in existing stages, not mandatory stages. A small change can reuse the baseline and existing contracts. Early feasibility does not require a frozen spec or final prototype; a final UI contract does consume the approved design.

## Working procedure & engineering laws

1. **Frame the decision, adaptive HLD/LLD & industry archetype.** Read supplied versions of business goals, constraints, existing code, deployment config and accepted ADRs. Identify the surface (UI, API, CLI/SDK, batch, stream, native or AI/model) and load only the matching domain rules in [industry-architecture-sops.md](references/industry-architecture-sops.md) (aligned with [industry-playbooks.md](../sdlc/references/routing/industry-playbooks.md)). Scale depth to lane `L0–L4`: `product_root/architecture.md` + `contract.md` carry **HLD** (problem/out-of-scope/metrics, style/responsibilities, dataflow + throughput estimate, API/auth/versioning/rate-limit, NFR/SLO/security, milestones/go-no-go), while `contract.md` + `T-<n>` tickets carry **incremental LLD** (interfaces/DI, `dba` schema/index/migration ref, non-trivial algorithm complexity/bounds, **Error Classification → Retry/Circuit-Breaker/Fallback/User-Visible Error table**, and **Unit/Integration/Contract/Mock boundary strategy**). Separate observed facts, assumptions and targets; name missing evidence.
2. **Derive deep boundaries, measurable bounds & NFR Exit Gate.** Define measurable quality scenarios, capacity derivations, **Bounded Everything** caps (query limits, timeouts, concurrency semaphores, retry jitter, AI token/step budgets), and a core fail-fast vs non-core **Graceful Brownout** ladder ([quality-attributes.md](references/quality-attributes.md)). **Hard NFR Exit Gate:** `backend` / `frontend` / `qa` must trace every `NFR-n` to a concrete design decision + numeric target (`"知道要快但没具体数字"` = immediate block). Derive **Ousterhout Deep Modules** (`hidden complexity ÷ interface surface`) that pass the Deletion Test, minimize connascence, enforce `Domain/Service -> Narrow Port <- Adapter` (DIP/ISP/LoD/LSP), and assign one **SSOT (DIE)** per invariant, visibility predicate, limit, and error catalog while avoiding premature boolean-flag helpers (**AHA**) ([boundary-derivation.md](references/boundary-derivation.md)).
3. **Resolve consequential uncertainty.** Inspect existing evidence first. If insufficient, run a bounded, isolated experiment under the packet's write scope and resource budget; retain command, environment, inputs and raw results. An unavailable experiment remains `unverified`, never a fabricated measurement.
4. **Decide state, statelessness & Three-State effects.** Reuse an applicable accepted ADR when its baseline assumptions still hold; on unresolved or net-new trade-offs, compare credible options and record **rejected alternatives + rejection reasons** and revisit triggers ([adr-and-tradeoffs.md](references/adr-and-tradeoffs.md)). Enforce **strict backend process statelessness** across horizontal replicas (forbid mutable session, progress, rate-limit, or coordination locks in process globals/`dict`/`RLock`). Keep external side effects outside DB transactions under the **Three-State Effect Protocol (`Success / Fail / In-Doubt`)**: persist intent + idempotency key first, and reconcile receipts on timeout (`In-Doubt`) before retrying. Refer business, security or irreversible trade-offs to their decision owner; a technical limit never authorizes changing GWT unilaterally.
5. **Executable Contract Lock & boundary parsing.** Commit machine-readable contracts (`OpenAPI / JSON Schema / Protobuf`) to git as the executable SSOT — generating frontend TS types + mocks for parallel `frontend`/`backend` build, gated by backend contract tests + CI lint/breaking-change checks via `scripts/check-contract.py` (`extra_gates: [contract]`). Enforce **Contract-First Edit Discipline** (`先改契约文件 → 重新生成类型与跑契约测试 → 再改业务代码；新增向后兼容，删改字段走新版本或 expand-contract`). Untrusted inputs **Parse, Don't Validate** once at the boundary into narrow types, Branded IDs, and status-discriminated unions, locking all 4 rework checklists (types/units, pagination/sort defaults, distinguishable `code`s, nulls & `DELETE` idempotency) and strict **CQS** ([contract-design.md](references/contract-design.md)). Hand data semantics to `dba` and metric/event semantics to data owners. Produce complete journey slices with one `slice_integrator`.
6. **Close the loop.** Declare deliverables, verification obligations, owners and due points. Keep `proposed`, `accepted`, `implemented` and `deployed` facts distinct; update current baseline facts only from evidence. When an input changes, route affected contracts, designs, tickets and checks for revalidation.

## Gotchas — security & recovery blind spots

Read [threat-model.md](references/threat-model.md) for station-by-station lifecycle security (`define` sensitive-data tagging → `shape` STRIDE/PASTA `[SEC-n]` ACs → PR `SAST`/dep scan → Staging `DAST` → periodic/major-release pen-test hook) and the **Least-Privilege Identity Audit** (deploy, DB migration vs app runtime, collector task, and service-to-service callers). Q2/Q3/Q4 are minimum triggers, not an exhaustive threat model; if a new trigger is discovered, return it to the manager to update `q_security` without editing workflow state yourself. Security controls require an implementation owner, verification and explicit residual-risk authority. Do not open `shape/security-review` for changes with no auth, privacy or supply-chain surface, and do not add its file to an ordinary shape gate.

For shared resources or recoverable multi-step state, distinguish task ownership, intermediate visibility, crash recovery, publication and downstream commitment. State which dependency a stop protects and what allows recovery; keep independent work available. Never treat a replay plan, single-key rename, or in-memory lock as a cross-process transaction guarantee ([adr-and-tradeoffs.md](references/adr-and-tradeoffs.md)).

## Handoff and authority

| Partner | Exchange |
|---|---|
| pm / designer | Business constraints, feasibility options and brownout UX; they own scope/GWT and experience decisions |
| dba / data owners | Fact ownership, invariants, tenancy matrix, access patterns, lifecycle and event semantics; reference their schemas/dictionary without copying |
| frontend / backend / algo / miner | Versioned narrow contracts, stateless/three-state obligations, complete slice tickets, final UI source where applicable, fitness checks |
| qa / sre | Quality/security obligations, failure-injection scenarios (`In-Doubt`, brownout, cross-tenant), operational budgets and raw evidence |
| reviewer / manager | Changed files, decision authority, unresolved risks, stale consumers and conformance results; independent acceptance remains theirs |

Write only the packet's `deliverable_paths` and owned `product_writes`, including declared spike files. Production code and physical schemas belong to their implementing owners. Return product-delta rows to the manager; do not write manager-owned logs or state.

## Excellence and self-check

- [ ] Decision and consumer impact are explicit; scope matches the assigned task and domain archetype ([industry-architecture-sops.md](references/industry-architecture-sops.md)).
- [ ] Every changing fact, visibility predicate, limit, and error catalog has one canonical SSOT (DIE); shallow pass-through wrappers eliminated via Deletion Test.
- [ ] Backend processes remain stateless across replicas; external side effects stay outside DB transactions with `Success / Fail / In-Doubt` recovery and bounded budgets/brownout.
- [ ] Contracts lock machine-readable `OpenAPI / JSON Schema / Protobuf` in git (contract-first edit discipline + 4 rework checklists), map every `NFR-n` to a concrete decision + numeric target, and cover Error → Retry/Circuit-Breaker/Fallback/User-Error + Unit/Integration/Contract/Mock boundaries.
- [ ] Each unknown, `[SEC-n]` control, least-privilege identity check and verification obligation has an owner and due point; absent evidence stays `unverified`; `proposed ≠ accepted ≠ implemented ≠ deployed`.
- [ ] For `verify/security-audit` (`04-verify/security-audit.md`): `sec_quickscan.py` clues triaged via semantic STRIDE/trust-boundary review, secrets redacted, and strictly defensive static only (zero active probing/exploitation/attack automation).

## Deep references & templates — load only for the assigned work

| Reference / Template | Use |
|---|---|
| [lifecycle.md](references/lifecycle.md) · [conformance-task.md](references/conformance-task.md) · [deepening.md](references/deepening.md) | Task procedures, spike limits, conformance tiers, and cycle hot-spot deepening |
| [industry-architecture-sops.md](references/industry-architecture-sops.md) | Concrete architecture SOPs across the 9 standard industry archetypes |
| [quality-attributes.md](references/quality-attributes.md) · [adr-and-tradeoffs.md](references/adr-and-tradeoffs.md) | Measurable QAS, capacity, consistency, Three-State effects, statelessness, and brownout |
| [boundary-derivation.md](references/boundary-derivation.md) · [contract-design.md](references/contract-design.md) | Deep modules, connascence, SOLID/LoD, DIE/AHA, executable API/SSE/CLI-SDK/event contracts |
| [threat-model.md](references/threat-model.md) · [diagrams.md](references/diagrams.md) | Station-by-station security, least-privilege identity audit, `[SEC-n]` deltas, and canonical SVG views |
| [templates/architecture-baseline.md](templates/architecture-baseline.md) · [templates/architecture-feasibility.md](templates/architecture-feasibility.md) | Product baseline and `define/feasibility` report |
| [templates/contract.md](templates/contract.md) · [templates/api-contract.md](templates/api-contract.md) · [templates/adr.md](templates/adr.md) · [templates/story.md](templates/story.md) | `shape/contract` HLD/LLD deliverables; omit inapplicable sections with a 1-line reason |
| [templates/security-review.md](templates/security-review.md) · [templates/architecture-change-impact.md](templates/architecture-change-impact.md) · [templates/architecture-conformance.md](templates/architecture-conformance.md) | Conditional security delta, mismatch impact routing, and `verify/conformance` report |
| `scripts/check-contract.py` | Mechanical lint & breaking-change gate for git-committed OpenAPI / JSON Schema / Protobuf contracts (`extra_gates: [contract]`) |

Reviewers use [references/role-quality.md](references/role-quality.md) ("Expert Bar vs Mediocre Order-Taker + Second-Order Scan") to evaluate these artifacts.
