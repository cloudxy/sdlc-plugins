# Product surfaces — multi-surface probe card (Discuss-S)

For a new product or a new surface, walk every applicable block below: explicit `N/A + reason` is fine, silent skip is not. For a bounded change, probe only the rows the change touches and state in one line why the rest are unaffected. Answers become FR/NFR in `define`, not GWT here. Pair with the active archetype in [industry-product-sops.md](../../prd-gwt/references/industry-product-sops.md).

## 1. Actor map (draw first — never collapse into generic "user")

| Role | Ask | Typical failure |
|---|---|---|
| Buyer / Economic owner | Who pays or approves budget, and what proves ROI/compliance? | Built for end users; procurement or security review blocks purchase |
| End-user / Consumer | Who uses weekly, and what is the fastest path to Aha? | Spec written in buyer/admin jargon; daily workflow is clunky |
| Tenant / Workspace admin | Who provisions SSO/RBAC, quotas, billing and audit logs? | Provisioning or permission change requires manual engineering tickets |
| Supply / Counterparty (multi-sided) | Who provides inventory, content, fulfillment or liquidity? | Demand side polished while supply onboarding or payout bleeds |
| Developer / Integrator (API/CLI/SDK) | Who integrates, debugs 4xx/webhooks, and upgrades versions? | Breaking payload or silent rate-limit breaks downstream automation |
| Platform operator | Who handles catalog, abuse/moderation, billing disputes or kill-switches? | Tenant admin conflated with platform superuser, leaking cross-tenant data |

## 2. Surface-specific probes

- **ToB / Multi-tenant SaaS:** tenant isolation boundary · RBAC/ABAC (`loading/unknown` vs `denied` vs `allowed` UI states) · SSO/invite/SCIM · seat/quota overage (grace / degrade / hard block) · audit log retention · empty-tenant first success vs historical import · deprecation notice SLA.
- **ToC / Consumer & Social:** `<30s` cold-start Aha before signup/paywall · empty-graph starter experience · UGC report/block/moderation/appeals · minor/PII consent · anti-sybil share/invite loops · notification opt-out & frequency caps.
- **Multi-Sided Marketplace & Fintech:** which side moves first this slice · cross-side liquidity bottleneck · coupon/subsidy stacking & negative-margin circuit-breaker · fund lifecycle & partial-refund/chargeback invariants · T+0/T+1 cutoffs · reverse-logistics/dispute arbitration.
- **AI Agentic & AIGC Workbench:** probabilistic eval threshold vs deterministic shell · prompt-injection & Human-in-the-Loop (HITL) confirmation before side-effects · token/GPU COGS per task · AIGC 5-state separation (`draft` / `submitted` / `in-flight` / `current output` / `history`) · asset lineage, provenance & commercial rights · salvage without double-billing quota on partial save failure.
- **Headless API / CLI / SDK / Data Feed:** machine contract (`--json` stdout vs human stderr, deterministic exit codes, idempotency keys, pagination/rate-limit headers) · SemVer & dual-run deprecation window · data freshness/completeness/backfill SLAs · parser-drift quarantine before overwriting good downstream partitions.
- **Client / Mobile / Desktop / IoT / Local-First:** offline read/write scope & reconnect conflict resolution (never silent data loss) · OS permission `denied / revoked` recovery · N-2 old-client server compatibility · store-review lead time & remote kill-switch / forced-upgrade floor.

## 3. Shared discipline

- **Observable outcome + paired counter-guardrail:** every target improvement names what must *not* degrade (e.g., conversion ↔ refund/churn, AI speed ↔ acceptance/COGS).
- **Triage non-product asks (YAGNI):** if the product already does it and users cannot find or understand it, route to `designer` (IA) or `ops` (`enablement`), not a new feature build.
- **Unified language:** use the same domain terms across marketing, admin, client UI and `<product_root>/domain-model.md §2`.
