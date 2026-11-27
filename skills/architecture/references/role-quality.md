# Architect review criteria

Single source of procedure: [Architecture — Excellence and self-check](../SKILL.md#excellence-and-self-check) and [lifecycle.md](lifecycle.md). Reuse of a valid accepted ADR, a multi-module FR, or an API-only slice is a sound choice when evidenced — never score architecture by document length, diagram count, or microservice count.

## Expert Bar vs Mediocre Order-Taker

| Dimension | Expert Architect Bar | Mediocre Order-Taker Anti-Pattern |
|---|---|---|
| **Module Depth & Connascence** | Deep modules (`hidden complexity ÷ interface surface`) passing the Deletion Test; static Name/Type connascence at seams; strict `Domain/Service -> Narrow Port <- Adapter` (DIP/ISP/LoD) | Shallow 1-FR-1-module pass-through wrappers; leaky ORM/dict interfaces; circular runtime or event loops disguised as clean folder trees |
| **Authority & DIE vs AHA** | One canonical SSOT per invariant, visibility predicate, quota, and error catalog (DIE); keeps incidentally similar code for diverging business actors separate (AHA); OCP only for ≥2 known or Next/Later variants | Duplicating "visible/published" filters or limits across endpoints; premature boolean-flag helper abstractions or speculative plugin frameworks |
| **State, Statelessness & Effects** | Strict backend process statelessness across horizontal replicas; external calls outside DB tx under **Three-State Protocol (`Success / Fail / In-Doubt`)** with durable intent + reconciliation | Holding session/progress/locks in process globals or `RLock`; treating HTTP timeouts as `Fail` and blindly retrying non-idempotent side effects |
| **Contracts & Type Safety** | **Parse, Don't Validate** at trust boundaries; discriminated unions eliminate illegal boolean combinations; explicit CQS (`GET`/probe zero side effects), N-2 compatibility, SSE/CLI/IPC rules | Happy-path-only JSON examples; optional-field soup; client-supplied `tenant_id` trusted without server session binding |
| **Bounds, Security & Lifecycle** | Bounded queries/queues/retries/token budgets + core vs non-core **Graceful Brownout**; delta `[SEC-n]` with owner/test/residual-risk authority; `proposed ≠ accepted ≠ implemented ≠ deployed` | Vague "high concurrency" claims; generic STRIDE copy-paste; reporting config manifests or cancelled plans as deployed topology |

## Task-Specific Review Gates

- **`define/feasibility`**: Falsifiable claim, bounded isolated spike (never installed into prod), raw outputs retained, unavailable target hardware marked `inconclusive` — zero unilateral GWT cuts.
- **`shape/contract` & `security-review`**: Every declared file exists in packet; data semantics handed to `dba` without dictating table columns; `[SEC-n]` names implementer, negative check, and external residual-risk approver.
- **`shape/change-impact` & `verify/conformance`**: Accepted contract stays frozen while owner approval is pending; conformance separates static code, executed revision checks, and identified running builds (`unverified` blocks sign-off).

## Second-Order Scan (Run Before Sign-Off)

1. **`In-Doubt` & Crash Window**: If the process crashes or times out right after sending an external call/publish, how do we avoid double-charging, lost work, or stuck leases?
2. **Multi-Replica Reality**: When `workers >= 2` or rolling `N-1` and `N` run concurrently, what breaks in memory, cache invalidation, or wire/schema compatibility?
3. **Rule Drift Vector**: If `pm` updates a permission, visibility, or pricing rule next month, will engineers have to remember to edit >1 place?
4. **Hot-Spot & Adversary Abuse**: What happens under 10x skew (hot SKU, celebrity fan-out, noisy tenant, runaway agent tool loop, untrusted IPC/URI input)?
5. **Domain Archetype Fit**: Have the concrete invariants for this domain in [industry-architecture-sops.md](industry-architecture-sops.md) been addressed and handed cleanly to `dba`, implementers, `qa`, and `sre`?

## Immediate Return-for-Rework Triggers

- Unilaterally weakening GWT or synchronous user behavior because of a technical obstacle without `pm` / decision-owner approval.
- Treating single-process memory/locks as cluster coordination, or placing external HTTP/MQ calls inside DB transactions without `In-Doubt` recovery.
- Duplicating canonical schemas, GWT tables, or visibility predicates instead of linking their single authoritative version (DIE).
- Marking `planned` checks, config files, or unexecuted device/load assumptions as `met` or `deployed`.
