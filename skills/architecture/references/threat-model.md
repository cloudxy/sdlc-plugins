# Threat model — risk-based trust and control analysis

Read when the change affects assets, trust, privilege, credentials, data sensitivity, dependencies or security configuration. Q2 auth/tenant, Q3 external contract and Q4 irreversible operation are the minimum triggers for `q_security: yes`. PII retention or consent, and a new external dependency or vendor lock, also select `shape/security-review` even when they do not by themselves set `q_security`. If the workflow flag missed a relevant change, return the trigger to the manager to update `q_security` before closing shape. The architect defines controls; implementation owners implement, QA/SRE verify, and the authorized decision owner accepts residual risk. No new mandatory role.

The manager dispatches `shape/security-review` only for those surfaces. A static copy or internal style change does not get the task, does not add `02-shape/security-review.md` to the shape gate, and does not widen the test set. Do not set `q_security` only to schedule the review. `q_security` stays Q2/Q3/Q4 and still requires the contract trust-boundary diagram on its own.

## Station-by-station lifecycle security chain

Security is wired into every station seam rather than bolted on as a pre-release surprise:

| Station | Mandatory Security Obligation | Artifact / Gate Anchor |
|---|---|---|
| `define` | **Sensitive-data tagging:** classify PII, credentials, financial/ledger data and tenant-confidential fields; declare purpose minimization, retention window and consent rules | `01-define/spec.md` §6 (NFR-04/05/06) |
| `shape` | **STRIDE / PASTA → verifiable `[SEC-n]` ACs:** model changed trust boundaries & abuse paths (STRIDE technical threats + PASTA business-impact abuse cases) and convert every mitigation into a testable `[SEC-n]` obligation | `02-shape/contract.md` §8 / `02-shape/security-review.md` |
| `implement` (PR) | **Shift-left static & supply-chain checks:** run scoped `SAST` rules, secret detection and dependency/lockfile vulnerability scan on touched code & packages | `03-impl/*evidence*.md` + PR/config `lint` gate |
| `verify` (Staging) | **Runtime control & `DAST` verification:** execute negative `[SEC-n]` cases (cross-tenant IDOR, direct HTTP bypass, revoked token) + Staging `DAST` scan on exposed HTTP/API surfaces where applicable | `04-verify/coverage.md` §1e + `test-report.md` |
| `deliver` / Major release | **Penetration-test hook & residual sign-off:** trigger periodic or major-release pen-test / red-team review for high-exposure surfaces (Q2/Q3/Q4, regulated/fintech) and verify authorized sign-off on any residual risk | `06-deliver/readiness.md` + `release-opinion.md` |

## Least-privilege identity audit

Whenever a change introduces or modifies runtime, data, pipeline or deployment credentials, audit and isolate **four distinct identity classes** (never share one omnipotent database or cloud key):

1. **Deploy / CI account:** scoped strictly to artifact upload, migration job trigger and rollout orchestration — zero interactive production data dump or runtime user-token minting.
2. **DB migration account vs App runtime account:** DDL privileges (`CREATE / ALTER / DROP / GRANT`) belong exclusively to the migration identity during controlled release windows; the **app runtime account** holds least-privilege DML only (`SELECT / INSERT / UPDATE` and explicit `DELETE` where business rules allow — zero DDL, zero superuser / RLS-bypass).
3. **Collector / batch task account:** restricted to designated source read cursors or append-only sink topics/staging tables; isolated from core OLTP mutation privileges.
4. **Service-to-service callers:** authenticated per caller (mTLS, short-lived workload JWT or scoped API credential) against an explicit endpoint/topic allow-list — never a shared cluster-wide static admin secret.

## Walk

1. Identify changed assets (from `define` sensitive-data tags), actors, data flows and failure/abuse consequences. Reuse the existing model when applicable, recording the delta.
2. Mark trust boundaries wherever trust assumptions or privilege change, including inside your own code: tenant-to-tenant, low-privilege worker-to-admin service, process/container, CI-to-production, secret store and agent-to-tool. Repository ownership is not the boundary criterion.
3. Apply relevant **STRIDE / PASTA** analysis: business-objective abuse path (PASTA) + spoofing, tampering, repudiation, disclosure, DoS and elevation of privilege (STRIDE), plus the 4-identity least-privilege audit above. Name attack/precondition/impact and convert each control into a verifiable `[SEC-n]` AC; a six-letter checklist alone is not a threat analysis.
4. Apply only the cross-cutting sections below that this change actually touches. Record the result with the `security-review` delivery contract. Diagrams are views, not another source of control definitions.
5. Assign mitigation, implementation owner, test/verification owner, evidence due point and residual risk decision. Route new NFR/acceptance requirements to PM; never silently edit their spec.

Depth follows impact, exposure, privilege, data sensitivity and recoverability, not a fixed timebox or the number of boundaries. A single privileged endpoint may need extensive analysis. For AI tools, enforce path/action/data scope outside the prompt, constrain privileges and model untrusted inputs. Secrets and sensitive data must not leak into diagrams, test logs or error examples.

## Authentication, session and authorization

Apply when identity, session, role or tenant scope changes. Skip this section when none of those change.

- Expiry, revocation and reuse: a session or token must stop working after logout, expiry or a privilege change. Name the check that proves a revoked credential is rejected.
- Server-side tenant and role checks on every object access, including ids the client supplies. A hidden control is not an IDOR or cross-tenant control.
- Browser and callback edges: CSRF on state-changing cookie calls, a CORS allow-list that does not reflect the request origin, and a redirect or callback allow-list.

## Privacy, retention and consent

Apply when the change collects, exports, logs or retains personal data.

- Minimize fields to a named purpose. A personal field with no purpose in this change stays out of the delta.
- State the retention period and the deletion or anonymization path. When an immutable audit log must keep a fact the privacy rule says to delete, record the conflict, who decides, and the chosen rule. Do not silently keep or drop the field.
- Redact personal data in logs, screenshots and error examples. Evidence samples use stand-in values.

## Dependencies and supply chain

Apply when a new external dependency or vendor lock is introduced.

- Pin the source (registry, URL, commit or version) and record the digest check the project already uses. Do not invent a second pinning scheme.
- Record license obligations that constrain distribution, and the decision owner who accepts them.
- Keep this repository's vendor lock and the rule against automatic installs: a searched skill stays read-only until a maintainer installs it. Install scripts do not receive production credentials. Separate the install identity from runtime secrets.

## `security-review` delivery contract

Write `02-shape/security-review.md` only as the delta against the existing authoritative security model. Link that model's version. If none exists, say so once and record this feature's obligations; do not paste an unrelated full model. Each `[SEC-n]` names the implementation owner, where verification evidence will land, and who may accept residual risk. The architect does not accept that risk. At shape, planned checks and owners are enough. At verification, missing runtime evidence stays unverified, not a pass.

| ID | Asset / boundary | Threat and impact | Control / canonical source | Implementation owner | Verification / owner | Residual risk / authority |
|---|---|---|---|---|---|---|
| [SEC-n] | <named flow> | <attack and consequence> | <enforcement point> | <role> | <case, expected result, evidence path> | <decision record or pending> |

## Verification and review

At shape, planned checks and responsible owners are acceptable; at the required verification point, demand actual current evidence. Missing runtime evidence is unverified, not a passing security claim. Reviewer dimension 4 checks boundary → control → implementation → test/result → residual authority, including the auth, privacy and supply-chain sections above when `security-review` is in scope, and including changed internal boundaries. Severity follows plausible impact and exposure; unresolved critical authorization/isolation risks block dependent work. Follow project red lines and existing risk-acceptance authority; the architect does not self-waive them.

Use the existing contract as the default output when no separate review was selected. Large projects may link a dedicated canonical model if already present or explicitly scoped in the packet; do not create duplicate security truth. Method background: [OWASP threat modeling process](https://community.owasp.org/Threat_Modeling_Process).
