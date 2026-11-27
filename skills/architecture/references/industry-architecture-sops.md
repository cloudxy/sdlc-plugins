# Industry Architecture SOPs — 9 Domain Archetypes

Select only the archetype(s) matching the product or slice surface (cross-domain orchestration: [industry-playbooks.md](../../sdlc/references/routing/industry-playbooks.md); physical data invariants: [industry-data-sops.md](../../schema/references/industry-data-sops.md); implementation & failure-injection proof: [industry-delivery-sops.md](../../impl-evidence/references/industry-delivery-sops.md)). Hybrid products combine only the touched archetypes (e.g. B2B SaaS + AI Agentic). Do not copy irrelevant archetypes into `contract.md`.

---

## 1. `b2b-saas` — Multi-Tenant Enterprise & Collaboration

- **Trust & Tenancy Boundary**: Resolve `tenant_id`, `org_id`, and actor claims exclusively from server-verified session/token context at the ingress boundary; never trust `tenant_id` in request bodies, query params, or client headers unless validated against actor membership.
- **Authorization Model Selection**:
  - **RBAC**: Fixed org roles (`owner`, `admin`, `member`, `viewer`) when permissions map cleanly to org-wide actions.
  - **ABAC**: Policy predicates over resource attributes (department, region, environment, data sensitivity, plan tier).
  - **ReBAC**: Hierarchical or graph sharing (`org -> workspace -> folder -> document`, guest invites, team ownership transfer). Define deterministic precedence (`explicit deny > resource grant > inherited workspace role`) and hand the exact visibility predicate to `dba` as a single canonical read model (DIE/SSOT).
- **Enterprise Identity & Session Lifecycle**: SSO (OIDC/SAML) + SCIM deprovisioning must revoke active sessions, refresh tokens, and API keys within a bounded window; role downgrade invalidates cached permission claims immediately.
- **Noisy-Neighbor Isolation**: Enforce per-tenant rate limits, concurrency semaphores, export/job queue quotas, and webhook outbound circuit breakers (HMAC signature + timestamp replay window + exponential backoff + DLQ).

## 2. `fintech-ledger` — Payments, Billing, Wallets & Clearing

- **Two-Phase Funds Movement**: Separate intent/reservation from settlement (`Authorize/Hold -> Capture/Settle` or `Reserve -> Post -> Payout`). Never combine external gateway HTTP calls inside a database transaction.
- **Compensation-Only Recovery**: Posted financial records are **immutable**. Refunds, chargebacks, fee adjustments, and error corrections execute exclusively via **compensating/reversing journal entries** referencing the original transaction ID — never `UPDATE` or `DELETE` historical entries.
- **Three-State Effect Protocol (`Success / Fail / In-Doubt`)**: Persist the payment/payout intent with a canonical `Idempotency-Key` scoped to `(tenant_id, caller, operation, key)` + request payload hash **before** calling an external rail. Any read timeout, connection drop, or 5xx after dispatch enters **`In-Doubt`**: recovery must query the provider's status endpoint or await settlement webhook before retrying or releasing held funds.
- **Exact Arithmetic & FX Snapshots**: Represent money strictly in integer minor units (or exact fixed-scale `DECIMAL`) paired with ISO-4217 `currency`; cross-currency flows snapshot `fx_rate`, `fx_source`, and `fx_quoted_at`.
- **T+1 Three-Way Reconciliation**: Mandate automated reconciliation across `(Business Order/Intent <-> Internal Double-Entry Ledger <-> External Gateway/Bank Statement)` with quarantine alerts and break-resolution SOPs before auto-payout.

## 3. `ecommerce-marketplace` — Catalog, Inventory, Pricing & Fulfillment

- **Three-Tier Inventory Architecture**: Separate `on_hand` (physical warehouse truth), `reserved` (locked by unpaid/unshipped checkout with explicit `expires_at` TTL), and `available = on_hand - reserved`. For flash-sale / hot-SKU contention, isolate admission via bucketed inventory reservations or serialized queue workers rather than unbounded row-lock stampedes.
- **Order Split & Snapshot Isolation**: Separate buyer-facing `checkout_order` (payment & buyer total) from merchant/warehouse `fulfillment_sub_orders` (split by seller, warehouse, or shipping temperature). Snapshot SKU title, spec, unit price, tax rate, and **item-level allocated discount/shipping** (penny-exact conservation: `Σ line_payable == order_payable`) at checkout so partial refunds/cancellations remain deterministic even after catalog edits.
- **Checkout Compensation Saga**: Coordinate `coupon lock -> inventory reserve -> payment intent` with explicit timeout sweepers that release inventory and coupons only after verifying payment is not `In-Doubt`.

## 4. `consumer-social` — High-Read Feeds, UGC & Real-Time Interaction

- **Multi-Tier Cache Coherence**: Define explicit staleness budgets across `CDN -> L1 in-process bounded TTL -> L2 Redis -> Primary/Replica DB`. Protect hot keys with singleflight mutexes or logical expiry + jittered TTLs; specify `read-your-own-writes` routing (e.g. author's fresh post merged from write-through token/primary window) so creators never see stale empty states after posting.
- **Hybrid Timeline Fan-Out**: Use push (`fan-out-on-write`) for normal-graph authors and pull (`fan-out-on-read` merge) for high-follower / celebrity accounts above a configured follower threshold to prevent write-amplification storms.
- **Graceful Brownout & Load-Shedding Ladder**: Classify dependencies into **Core** (auth, feed read, post publish) vs **Degradable** (personalized reranking, view counters, online presence, related recommendations). Under latency/error budget burn, shed degradable calls automatically to deterministic fallbacks before core availability degrades.
- **UGC Moderation Boundary**: Newly submitted UGC/media enters `pending_review` / author-only visibility until synchronous safety gates pass; async takedowns propagate cache invalidation across CDN and feed indexes.

## 5. `ai-agentic` — LLM Apps, RAG Pipelines & Autonomous Tool Agents

- **Streaming Transport Contract (SSE / WebSocket)**: Define typed frames (`meta`, `delta`, `tool_call`, `tool_result`, `citation`, `usage`, `error`, `done`), `trace_id`, reconnection/resume semantics, proxy anti-buffering (`X-Accel-Buffering: no`), and mid-stream error frames (once HTTP `200` headers flush, upstream failures or budget trips must emit `event: error` with stable `code`, never silent stream cutoff). Propagate client disconnect (`AbortSignal`) to cancel upstream generation.
- **Tool Sandbox & HITL Authorization**: Classify every agent tool into:
  1. `Read-only` (scoped to caller's tenant/ACL **outside** the prompt),
  2. `Reversible write` (scoped workspace/draft with undo),
  3. `Irreversible / external side-effect` (payment, email, external mutation, destructive delete — requires **Human-in-the-Loop (HITL) confirmation token** verified by deterministic server code, never LLM self-approval).
- **Token, Step & Cost Circuit Breakers**: Enforce hard per-run `max_steps`, `max_tool_retries`, `max_input_tokens`, `max_output_tokens`, wall-clock timeout, and per-tenant daily spend caps; detect repeated identical tool-call loops and abort cleanly.
- **Measurable Degradation Chain**: Pair every model capability with a versioned `eval-set` (`algo`) and an explicit runtime fallback chain (`primary model -> lower-latency backup model -> deterministic rules / honest abstention`).

## 6. `aigc-workbench` — Multimodal Generation, Editing & Media Pipelines

- **Async Job & Worker Lease Pipeline**: Model long-running image/video/audio/3D jobs as durable state machines (`queued -> leased -> generating -> postprocessing -> succeeded | failed | canceled`) with worker heartbeats, lease-expiry recovery, idempotent submission keys, and explicit user-cancel propagation. Separate no-cost capability probes from billable generation calls.
- **Derived-Asset Lineage & Rights Propagation**: Every transformation (`crop`, `inpaint`, `layer-split`, `upscale`, `stitch`, `remix`, `transcode`) produces a new immutable asset version linked to `parent_asset_ids` and **inherits source license/rights allowlists** through a canonical lineage resolver (DIE/SSOT) so downstream publish/export stages never hit unexpected `422` rights rejections or leak restricted reference assets.
- **Local / Cloud Media Staging & Integrity**: Keep **source business reference**, **immutable media bytes (content digest + length + MIME)**, and **consumer display/Range-streaming URLs** distinct. Require staging verification + grace window before garbage collection, disk free-space floor guards on local/edge volumes, and strict separation between system channel switches and explicit user-disabled models/providers.

## 7. `data-crawler` — External Acquisition, Scrapers & Event/Stream Ingestion

- **Watermarks, Checkpointing & Scoped Backpressure**: Bound every ingestion stage with per-source rate limiters, concurrency semaphores, and bounded queues. When a target host bans, rate-limits (`429`), or changes DOM/API schema, trip the circuit breaker **only for the affected source/account dependency** — independent healthy sources continue draining.
- **Three-State Extraction Contract**: Strictly separate `(1) confirmed non-empty payload`, `(2) confirmed valid empty result (HTTP 200, data=[])`, and `(3) missing field / malformed schema / auth block`. Never collapse `(2)` and `(3)`: `(2)` commits an explicit empty-window manifest; `(3)` raises a parser/contract alert without overwriting prior good snapshots.
- **Full-Identity Deduplication & Replayable Raw Archive**: Partition and deduplicate by the full request identity `(source, account/tenant, entity/geo_scope, metric, window)` + monotonic event/batch ID (never payload hash alone when identical values can recur legitimately). Retain raw response snapshots (bounded retention) so parser fixes replay deterministically without re-hitting external targets.

## 8. `regulated-compliance` — Healthcare, Gov, Enterprise Security & Audit

- **KMS Envelope Encryption & Key Boundaries**: Encrypt sensitive PII/PHI/secrets using per-tenant or per-domain Data Encryption Keys (DEKs) wrapped by HSM/KMS Key Encryption Keys (KEKs) with online key-version rotation. Where exact-match search on encrypted fields is required, use keyed HMAC blind indexes (separate key) and forbid plaintext leakage in logs, URLs, caches, analytics events, or 5xx traces.
- **Maker-Checker (Dual Control)**: High-privilege mutations (policy changes, bulk exports, manual balance/clinical overrides, key rotation) require a server-enforced two-actor state machine (`proposed by actor A -> approved by distinct authorized actor B`, `actor_a != actor_b`, immutable payload hash).
- **Break-Glass Emergency Access**: Emergency privilege elevation requires an explicit ticket/reason, short auto-expiring lease, real-time security alert, and 100% post-hoc review obligation.
- **DSAR Erasure vs Legal-Hold Separation**: Architect personal-data storage so GDPR/PIPL right-to-erasure (crypto-shredding or PII vault redaction) can execute cleanly while preserving immutable regulatory audit trails and active `legal_hold` exemptions — resolve retention conflicts explicitly with compliance/PM authority at `shape/security-review`.

## 9. `client-iot-localfirst` — Desktop, Mobile, Mini-Program, CLI, SDK & Edge

- **Untrusted IPC / Bridge Allowlists**: Treat Electron/Tauri IPC, mobile `JSBridge`, WebViews, Deep Links, and custom URI schemes as untrusted external boundaries. Enforce explicit command allowlists, caller origin checks, normalized path confinement (preventing `../` or symlink escapes), and OS permission denial/revocation recovery flows.
- **N-2 Wire Compatibility & Version Lifecycle**: Installed apps, SDKs, and IoT firmware cannot upgrade atomically with backend deploys. Maintain backward-compatible additive APIs across the supported `N-2` client window, negotiate capabilities explicitly, and provide a server-driven `min_supported_version` upgrade/degrade contract before retiring endpoints.
- **CLI & SDK Determinism**:
  - **CLI**: Pure structured output on `stdout` under `--json`, human logs/spinners/errors strictly on `stderr`, deterministic exit codes (`0` ok, `1` execution/domain error, `2` usage/schema error), `--no-input` / non-TTY safety, and explicit `--dry-run` (CQS).
  - **SDK**: Narrow typed surface (ISP), zero process-global auth state (explicit client instance config), injectable transport/timeout/retry policy, and typed error classes carrying `code` + `retryable` + `trace_id`.
- **Local-First Sync & Offline Resilience**: Decouple UI reads/writes onto a local persistent store (SQLite/IndexedDB) with sequential skipped-version migrations, append-only local outbox mutations (`client_mutation_id`), monotonic sync cursors, and deterministic conflict handling (`LWW` only for idempotent preferences; domain merge or explicit conflict copy for user-authored documents).
