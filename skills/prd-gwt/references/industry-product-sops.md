# Industry product, discovery, growth & enablement SOPs

Read the section matching `profile.industry` and any active `profile.traits` (`[multi-tenant, payments, ai-enabled, realtime, offline-first, regulated]` in `sdlc.config.yaml` / `state.yaml`; see [`skills/sdlc/references/routing/industry-playbooks.md`](../../sdlc/references/routing/industry-playbooks.md)). Apply only the rules relevant to the current slice; mark unused high-risk mechanisms `N/A` with a concrete reason.

## Cross-archetype product laws

1. **Falsifiability-first:** every bet, highlight and positioning claim states what observable result would prove it wrong before data arrives.
2. **Paired metric & counter-guardrail:** never optimize a target metric naked—pair every north-star/driver with the metric that catches gaming or collateral harm (conversion ↔ refund/churn, AI speed ↔ acceptance/COGS, push CTR ↔ opt-out/uninstall, GMV ↔ negative-margin subsidy).
3. **SVOT & SSOT:** domain terms cite `<product_root>/domain-model.md §2`; metrics cite `metric:<id>@v<n>` in `<product_root>/data/metrics.yaml` (never re-paste SQL/formulas in `spec.md`); signals cite `SIG-<yyyymm>-<n>`; status-quo evidence lives once in `compete.md` / `market.md` and is cited downstream.

---

## 1. `b2b-saas` ( & trait `multi-tenant` )

- **Persona & journey split:** separate **Buyer** (budget, ROI, security/compliance review), **Tenant Admin** (SSO/SCIM, RBAC/ABAC, seat/quota provisioning, audit log, billing) and **End-User** (weekly job-to-be-done Aha). Writing all FRs for generic "user" hides procurement and provisioning blockers.
- **Discovery & compete:** evaluate POC/pilot gating criteria, data import/migration switching cost vs empty-tenant first success (sample workspace/templates), and seat vs usage packaging friction.
- **PRD & permissions:** explicitly define cross-tenant non-leakage (`404` vs `403` policy), three permission states (`loading/unknown`, `denied` with who-can-grant, `allowed`), seat/quota overage behavior (grace period vs hard block vs read-only degrade), and admin audit events.
- **Metrics & paired guardrails:** Product-Qualified Account (PQA) activation, weekly active seats/paid seats, NRR/expansion ↔ tenant-admin ticket load, permission-request block rate, logo/seat churn.
- **Growth & enablement:** enterprise CS rollout kit, tenant-admin setup checklist, and contractual API/webhook/feature **deprecation notice windows** with dual-run migration paths.

## 2. `fintech-ledger` ( & trait `payments` )

- **Fund lifecycle state machine:** specify every state (`initiated → authorized → captured/settled → clearing → partially_refunded / refunded → disputed/chargeback → closed/failed`) and **illegal transitions** (e.g., late payment webhook arriving after cancel/timeout must record a late-callback event and trigger reconciliation/refund—never silently re-open or drop money).
- **Ledger & refund invariants:** conservation of funds (every state change maps to balanced accounting entries, never an arbitrary `set balance = X`), business-key idempotency on submit/retry/webhook, explicit currency minor-unit precision & rounding rules, and partial/full refund + fee-reversal + chargeback clawback semantics (`<= original captured amount`).
- **Cutoff & reconciliation:** define T+0 / T+1 settlement cutoffs, business-date timezone vs UTC event timestamp (`metrics-blueprint.md`), and user-visible pending vs settled balance copy.
- **Metrics & paired guardrails:** payment success / settlement completion rate ↔ reconciliation discrepancy count (must be `0`), duplicate-charge/refund error rate, chargeback/dispute rate, fraud loss rate.
- **Growth & enablement compliance:** strict ban on guaranteed-return, misleading yield/APR, or hidden-fee claims; CS scripts must cover pending-settlement anxiety, failed-debit reversal timelines, and account-freeze escalation without exposing internal fraud thresholds.

## 3. `ecommerce-marketplace`

- **Two-sided liquidity & scope:** declare whether this slice targets Demand (buyer), Supply (merchant/creator/provider), or matching/fulfillment, and state the cross-side impact; `market.md` declares addressable units per side separately.
- **Promo stacking & margin circuit-breakers:** specify exact coupon + platform subsidy + points + tier-discount stacking precedence, per-user/per-campaign caps, anti-arbitrage rules, and an automatic **negative-margin circuit-breaker** (hard halt when stacked discount breaches floor price).
- **Inventory & reverse-logistics flows:** specify stock hold/release timing, split-shipment / partial out-of-stock cancellation, and return / exchange / refund-only / platform-dispute arbitration state machines with timeout defaults.
- **Metrics & paired guardrails:** order conversion / GMV / take-rate / buyer-seller match liquidity ↔ subsidy-to-GMV ratio, net margin, return/refund/dispute rate, merchant stockout cancellation rate.
- **Enablement:** separate merchant-side operational SOPs from buyer-side self-service return/refund status clarity.

## 4. `consumer-social`

- **`<30s` cold-start Aha:** deliver tangible value before heavy signup, profile completion or paywalls; solve the empty-room / zero-follower cold start via curated starter content, templates or immediate creation output.
- **UGC trust, safety & appeals:** every UGC or social-interaction surface specifies `report / block / mute`, moderation visibility states (`public / limited-reach / under-review / removed`), non-opaque takedown notice + **user appeal path**, and minor/privacy protections.
- **Anti-sybil viral loops:** share/invite loops specify logged-out recipient landing experience (deep-link + preview without forced app install wall where web works) and anti-abuse rules (device/account deduplication, reward clawback on fake signups, rate limits).
- **Metrics & paired guardrails:** `<30s` activation rate, D1/D7/D30 cohort retention, K-factor (`invite_rate × invitee_activation`) ↔ push opt-out / app uninstall rate, UGC report/abuse rate, spam-invite rejection rate.
- **Growth:** strict cross-channel notification frequency caps, quiet hours, and behavioral trigger relevance over batch blasts.

## 5. `ai-agentic` ( & trait `ai-enabled` )

- **Probabilistic acceptance specs (never fake 100% deterministic GWT on open-ended generation):**
  1. **Deterministic envelope GWT:** tool-call permission checks, schema/citation link validity, timeout/fallback/retry behavior, max step/token budget circuit-breaker, and UI provenance labels (`AI 生成` / source citations).
  2. **Probabilistic quality contract:** bind a representative golden evaluation set (including adversarial/ambiguous/long-tail cases), explicit pass threshold (e.g., faithfulness `≥ X%`, rubric pass `≥ Y%`, abstention on missing context `≥ Z%`), and baseline comparison—routed to `algo` `evaluate` and `qa` `test-plan`.
- **Prompt-injection & HITL safety:** untrusted external content (retrieved docs, emails, web pages, tickets) cannot trigger privileged tool actions; consequential actions (send message, mutate external record, spend money, delete data) require explicit **Human-in-the-Loop (HITL) preview + confirmation** and reversible audit logs.
- **Unit economics & paired guardrails:** task resolution / user acceptance (kept-without-heavy-rewrite) / TTFT & end-to-end latency ↔ **token & inference COGS per accepted task**, hallucination/citation-mismatch rate, loop/retry amplification rate, human-takeover/thumbs-down rate.
- **Growth & claims ban:** **strictly forbid cherry-picked best-of-N outputs** in positioning, demos, screenshots or launch copy; claims must reflect median/verified golden-set behavior on realistic inputs and state failure/review boundaries.

## 6. `aigc-workbench`

- **Five-state workspace lifecycle:** explicitly distinguish (1) `current input draft` (prompt, refs, params), (2) `submitted snapshot`, (3) `in-flight generation job`, (4) `current active output`, and (5) `saved history / asset library`. Refresh, tab switch, or save failure must never wipe the draft or silently present an older history item as the newly generated result (`design-contract` interaction-preserving rules).
- **Multi-step derivation & commercial rights:** track asset lineage (`prompt / negative_prompt / model@version / seed / reference_asset_id → upscale / inpaint / remix / export`), commercial-use license & model/reference provenance, and block unauthorized real-person likeness or third-party trademark generation.
- **Async queue, quota & partial-failure recovery:** specify queue ETA/cancel, credit reservation vs deduction, automatic quota refund on system/provider failure, and **salvage without double-charging** when media bytes generated but library DB persistence or download failed; specify local/cloud storage quota warnings.
- **Metrics & paired guardrails:** usable-asset export/download/publish rate, multi-turn refinement completion ↔ credit/GPU cost per exported asset, queue abandonment rate, unrefunded-failure ticket rate.

## 7. `data-crawler`

- **Headless data-product journeys & SLAs:** journeys J-n describe data consumer workflows (downstream SQL/API/feed consumption, backfill request, anomaly alert response)—never invent UI screens for a headless pipeline. Specify **freshness SLA** (max staleness), **completeness/coverage bounds**, primary deduplication key + event-time vs ingestion-time semantics, and **historical backfill window**.
- **Source licensing, politeness & drift quarantine:** record source ToS / `robots.txt` / licensing / PII scrubbing rules; rate-limit budgets; and **parser-drift circuit-breakers** (when upstream HTML/API changes cause schema mismatch, null spikes or `>X%` row-count drop, quarantine the batch and alert—never overwrite healthy downstream partitions with empty/corrupt data).
- **Contract evolution:** downstream schema breaking changes require dual-column/versioned transition windows and explicit consumer notice in `enablement.md` / `release-notes.md`.
- **Metrics & paired guardrails:** partition on-time freshness rate, field completeness/accuracy ↔ quarantine/false-empty incident rate, source block/429 rate, cost per million valid records.

## 8. `regulated-compliance` ( & trait `regulated` )

- **Data classification & residency:** tag every new field by sensitivity (`public / internal / PII / sensitive-PII / PHI / financial-secret`), jurisdiction residency boundary (no cross-region replication/LLM-egress without explicit legal basis), and purpose-bound consent + retention TTL.
- **DSAR erasure vs immutable audit separation:** explicitly separate mutable personal profile/content stores (subject to GDPR/PIPL DSAR export & erasure/crypto-shredding within statutory SLA) from legally mandated immutable audit/ledger logs (protected by legal hold, storing pseudonymous actor IDs rather than raw erasable PII).
- **Maker-Checker (Four-Eyes) workflows:** high-risk operations (policy/limit overrides, bulk PII export, manual ledger adjustment, compliance rule edits) require distinct **Maker** (proposer) and **Checker** (approver) roles (Separation of Duties: creator cannot self-approve), mandatory reason text, approval expiry, and tamper-evident audit trail.
- **Non-waivable compliance gates:** NFR Security / Permissions / Compliance rows cannot be marked `N/A` without explicit compliance owner authority; growth/enablement copy requires substantiated regulatory disclaimers.

## 9. `client-iot-localfirst` ( & trait `offline-first` )

- **Offline sync & conflict resolution:** specify what works offline (read cache vs queued mutations), outbox retry/ordering when connectivity returns, and deterministic **conflict resolution UX** (CRDT / field merge / last-writer-wins only where lossless, otherwise preserve user's conflicting local draft as an explicit conflict copy—never silently discard user edits).
- **OS permissions & device hostility:** cover `not-determined → denied → revoked-in-OS-settings` recovery paths (camera, mic, BLE, location, local folder access) with deep-link/instructions; specify behavior under low disk, background process kill, clock skew, and captive-portal/flaky networks.
- **N-2 old-client coexistence & kill-switch:** shipped binaries/firmware/packages cannot be recalled instantly. Plan **server backward compatibility across `N` to `N-2` client versions**, minimum-supported-version forced-upgrade / feature **kill-switch** UX, and App Store / firmware signing lead times during `shape` (before coding).
- **CLI & SDK ergonomics (when `surfaces` includes `cli` or `sdk`):**
  - **CLI:** deterministic exit codes (`0` success, distinct non-zero for usage vs auth vs transient failure), `--json` structured stdout vs human progress/errors on `stderr`, non-interactive `--yes` / piped `stdin` support, `--dry-run` for destructive actions, `NO_COLOR`/TTY respect.
  - **SDK:** strict SemVer contract, typed error hierarchy with retryability flags, configurable timeouts/retries, zero-surprise upgrade guide & deprecation warnings in `enablement.md`.
- **Metrics & paired guardrails:** crash-free session/device rate, offline-sync convergence rate, CLI/SDK first-call success time ↔ sync conflict/data-loss ticket rate, old-version forced-upgrade drop-off, battery/storage regression.
