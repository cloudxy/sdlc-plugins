# Product surfaces — ToB / ToC probe card (Discuss-S)

Walk every row. N/A + reason is fine. Silent skip is not. Answers become NFR/FR in define, not here.

## Four roles (draw first)

| Role | Ask | Typical failure |
|---|---|---|
| Buyer | Who pays, what counts as value back? | Built for end users, procurement will not buy |
| User | Who uses weekly, what does success look like? | FR written in the buyer's words |
| Tenant admin | Who provisions, who sets perms, who sees audit? | C-end only; provisioning is a ticket |
| Platform admin | Who runs catalog / billing / ban? | Tenant admin = superuser, data leaks |

Both-sides product: which side this round, the other out of scope or parallel later.

## ToB

Tenant boundary · RBAC vs ABAC (unknown / deny / allow as three UI states) · SSO/invite/manual provision · packaging / seat overage (hard block / degrade / oversell) · audit who-did-what retention · webhooks/idempotency · empty-tenant first success vs must-import-history · SLA as degrade behaviour.

## ToC

Activation (first success while logged-out/unpaid) · growth loop in or out of scope this round · consent/PII/minors · paywall copy · notifications when disabled · public/share pages.

## Shared

North-star is an observable user change, not "we shipped an API". Instrumentation gaps go to define as FRs. If this feature *increases* support load, it may be docs/IA not a product FR (triage: existing capability). Same action, same term on marketing site, tenant admin, and C-end.
