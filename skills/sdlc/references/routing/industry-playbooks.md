# Industry playbooks & project profile router

Projects fail in predictable, domain-specific ways when every product is treated as a generic CRUD web app: an AI agent gets impossible 100% deterministic GWTs, a ledger skips partial-refund conservation, a B2B SaaS builds for end users while failing enterprise admin procurement, or a mobile/CLI release ships an irreversible binary without an N-2 compatibility or rollback plan.

`profile` in `sdlc.config.yaml` (mirrored into each feature's `state.yaml` as `project_profile`) routes hats to concrete domain checklists without bloating universal gates.

## 1. Canonical `profile:` schema (`sdlc.config.yaml`)

Use block-style YAML and scalar flow lists (no inline `{a: b}` dicts):

```yaml
profile:
  industry: b2b-saas             # Primary archetype (1 of the 9 locked IDs below)
  traits: [multi-tenant]         # Composable cross-cutting traits (0..6 from the locked set)
  surfaces: [web, api]           # Active user/consumer surfaces: web | mobile | desktop | cli | sdk | api | webhook | iot-firmware
  db_engines: [postgres, redis]  # Primary stores: postgres | mysql | sqlite | clickhouse | redis | vector | object-store
  architecture_style: modular-monolith  # modular-monolith | service-oriented | event-driven | serverless | local-first-sync | batch-pipeline
  compliance: []                 # Applicable regimes: soc2 | pci-dss | gdpr | pipl | hipaa | financial-audit
```

### Locked `industry` archetypes (9)

| `industry` ID | Typical product | Default implied risk focus | Primary failure mode when treated generically |
|---|---|---|---|
| `b2b-saas` | Multi-role workspace, admin console, subscriptions | Buyer ≠ admin ≠ user; tenant isolation; RBAC/audit; deprecation SLA | Built for single-user happy path; fails procurement, SSO/RBAC or tenant boundary |
| `fintech-ledger` | Payments, wallets, billing, clearing, invoicing | Double-entry conservation; idempotency; T+0/T+1 cutoffs; partial refund/chargeback | Mutable `balance` column, race-condition double-spend, late webhook corruption |
| `ecommerce-marketplace` | Two-sided store, booking, promos, fulfillment | Supply/demand liquidity; coupon stacking circuit-breakers; stock/reverse-logistics | Promo arbitrage drains margin; split-order/refund state deadlocks |
| `consumer-social` | Feeds, UGC creation, messaging, communities | `<30s` cold-start Aha; UGC moderation/appeals; anti-sybil loops; push fatigue | Heavy signup wall kills activation; unmoderated UGC or spam notifications spike churn |
| `ai-agentic` | Copilots, tool-using agents, RAG, autonomous workflows | Probabilistic evals; hallucination/citation bounds; injection refusal; HITL; token COGS | Fake deterministic GWT on LLM prose; cherry-picked demos; unbounded agent side-effects |
| `aigc-workbench` | Image/video/audio/3D generation & editing studio | Draft vs submitted vs current vs history state; asset lineage/rights; async quota recovery | Refresh overwrites draft or shows stale history as current; failed save double-charges quota |
| `data-crawler` | Scrapers, ETL/ELT feeds, market intelligence APIs | Freshness/completeness SLAs; source licensing/robots; parser drift quarantine; backfill | Upstream DOM change silently writes 0-row partitions over good downstream tables |
| `regulated-compliance` | Healthcare, gov/legal, enterprise GRC, licensed finance | Data residency; DSAR erasure vs immutable audit hold; Maker-Checker (SoD) | GDPR delete wipes legally mandated audit log, or single admin executes unchecked privilege |
| `client-iot-localfirst` | Mobile/desktop apps, offline-first tools, CLI/SDK, firmware | Offline sync conflicts; OS permission revocation; N-2 client coexistence; kill-switch | Forced breaking API bricks old clients in the wild; store review blocks emergency hotfix |

### Locked composable `traits` (6)

A project picks **one** primary `industry` and composes zero or more `traits` when secondary mechanics cross archetypes (for example, `b2b-saas` + `[ai-enabled, payments]`):

- `multi-tenant` — strict tenant-scoped queries, cache keys, background jobs, exports and RBAC/ABAC boundaries.
- `payments` — money movement, idempotent billing/webhooks, ledger reconciliation, partial refund/chargeback invariants.
- `ai-enabled` — LLM/ML inference in the loop: golden-set evals, fallback/abstention, prompt-injection defense, token/latency guardrails.
- `realtime` — WebSockets/SSE/collaborative presence, ordering/backpressure, reconnect state recovery, idempotent replay.
- `offline-first` — local persistence, optimistic queue, reconnect conflict resolution, schema forward-migration on client upgrade.
- `regulated` — PII/PHI/financial data classification, residency, DSAR vs audit separation, compliance sign-off on claims and N/A.

## 2. Progressive inference & Step 2 confirmation rule

1. **Non-blocking inference (`check_config.py`):** When `profile:` is absent or partial in `sdlc.config.yaml`, `check_config.py` inspects repository signals (lockfiles, `ui_paths`, `auth_paths`, ORM/migration engines, LLM SDKs, CLI entrypoints, mobile/desktop manifests) and emits `[推断] profile: ...` as an informational warning. **Ordinary local work (`L0`, `L1`, bounded `refine`/`fix`, prototype spikes, read-only `review-only`) is never blocked by an unset profile.**
2. **High-risk Step 2 confirmation:** During `/sdlc` Step 2 (or `/sdlc-product` preflight), the manager asks the operator to confirm `profile` **only** when the requested change touches a high-risk surface while `profile` is unset or still `[推断]`:
   - **Money / ledger / billing** (`payments`, `fintech-ledger`, `ecommerce-marketplace` checkout/promo)
   - **Multi-tenant auth / permission boundary** (`multi-tenant`, Q2 `auth/tenant`)
   - **Customer-facing AI launch or autonomous tool action** (`ai-enabled`, `ai-agentic`, `aigc-workbench`)
   - **Regulated PII / PHI / compliance obligation** (`regulated`, `regulated-compliance`)
   - **Irreversible schema/contract or client binary/SDK/firmware release** (`client-iot-localfirst`, Q3/Q4)
3. **Persistence:** Once confirmed by the operator, delegate the config write to SRE `ci` (or let the operator save `sdlc.config.yaml`), and snapshot the resolved fields into `<feature>/state.yaml` `project_profile` ([task-scope.md](../protocol/task-scope.md)). Never silently invent compliance or industry commitments without marking `[推断]`.

## 3. Shift-left triggers driven by `profile`

| Trigger in `profile` or Step 2 | Shift-left action before implementation | Stage / Hat |
|---|---|---|
| Unproven latency, LLM accuracy/cost, external crawl source, or sync engine | Dispatch `define/feasibility` before freezing spec commitments | `define` · `architect` (or `algo` `explore` when model/prompt feasibility) |
| `ai-agentic`, `fintech-ledger`, `multi-tenant`, complex state/concurrency | Invite `define/test-plan` to lock golden-eval / invariant / isolation oracles early | `define` · `qa` |
| Discovery `bet`, `consumer-social` / `ecommerce-marketplace` experiment, AI quality metric | Invite `define/measurement-plan` to pre-register metric, counter-guardrail & MDE | `define` · `analyst` |
| `client-iot-localfirst`, Q4 irreversible migration, public `api`/`sdk` contract | Design N-2 coexistence, feature kill-switch, expand-contract migration & rollback in `shape` | `shape` · `architect` + `dba` |
| `ai-enabled` / `ai-agentic` / `aigc-workbench` / `miner` ranking or model change | Select `algo` `explore` → `evaluate` (golden set + COGS/latency) or `diagnose` → `fix` | `shape` / `implement` / `verify` · `algo` |

## 4. Cross-stage domain SOP routing table

Hats do not load all four SOP catalogs—each hat reads only the domain SOP file matching its craft when `profile.industry` or `profile.traits` applies:

| Function / Stages | Participating hats | Domain SOP reference | What it governs |
|---|---|---|---|
| **Product, Discovery, Growth & Ops** (`discover`, `market`, `compete`, `growth`, `signals`, `define`, `accept`, `enablement`, `launch`) | `discover` manager, `researcher`, `competitor`, `growth`, `ops`, `pm` | [`skills/prd-gwt/references/industry-product-sops.md`](../../../prd-gwt/references/industry-product-sops.md) | Persona splits, value/Aha framing, probabilistic vs deterministic GWT, paired counter-guardrails, promo/AI claims bans, CS/API/deprecation enablement |
| **Architecture, Security & Contracts** (`define/feasibility`, `shape/contract`, `shape/security-review`, `shape/change-impact`, `verify/conformance`) | `architect`, `reviewer`, `qc` | [`skills/architecture/references/industry-architecture-sops.md`](../../../architecture/references/industry-architecture-sops.md) | Trust boundaries, tenant/auth isolation, idempotency/outbox, AI gateway/HITL sandboxes, N-2 compatibility, fitness functions & failure modes |
| **Data, Schema, Tracking & Warehouse** (`shape` dba/collect/warehouse, `implement` migrations/pipelines, `verify` data validation) | `dba`, `data-collector`, `data-warehouse-engineer`, `analyst` | [`skills/schema/references/industry-data-sops.md`](../../../schema/references/industry-data-sops.md) | Double-entry ledger tables, RLS/tenant keys, DSAR vs immutable audit separation, event/metric SVOT, crawl quarantine & point-in-time snapshots |
| **Implementation, Algo, QA & Release** (`implement`, `verify`, `deliver`) | `backend`, `frontend`, `algo`, `qa`, `sre`, `qc` | [`skills/impl-evidence/references/industry-delivery-sops.md`](../../../impl-evidence/references/industry-delivery-sops.md) | Concurrency/race tests, golden-eval harnesses, UI state isomorphism, staged canary/kill-switches, extra gates (`layering` / `frontend` / `explain`) & release rollback proof |
