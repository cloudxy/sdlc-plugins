# Threat model — risk-based trust and control analysis

Read when the change affects assets, trust, privilege, credentials, data sensitivity, dependencies or security configuration. Q2 auth/tenant, Q3 external contract and Q4 irreversible operation are minimum triggers. If the workflow flag missed a relevant change, return the trigger to the manager to update `q_security` before closing shape. The architect defines controls; implementation owners implement, QA/SRE verify, and the authorized decision owner accepts residual risk. No new mandatory role.

## Walk

1. Identify changed assets, actors, data flows and failure/abuse consequences. Reuse the existing model when applicable, recording the delta.
2. Mark trust boundaries wherever trust assumptions or privilege change, including inside your own code: tenant-to-tenant, low-privilege worker-to-admin service, process/container, CI-to-production, secret store and agent-to-tool. Repository ownership is not the boundary criterion.
3. Apply relevant STRIDE questions: identity/delegation (spoofing); integrity (tampering); attributable audit (repudiation); data minimization/isolation (disclosure); bounded resource use (DoS); least privilege and server-side authorization (elevation). Name attack/precondition/impact; a six-letter checklist alone is not a threat analysis.
4. Record `[SEC-n]` obligations in the canonical contract/security section. If a project already has an authoritative security model, link its version and record only this feature's delta. Diagrams are views, not another source of control definitions.
5. Assign mitigation, implementation owner, test/verification owner, evidence due point and residual risk decision. Route new NFR/acceptance requirements to PM; never silently edit their spec.

| ID | Asset / boundary | Threat and impact | Control / canonical source | Implementation owner | Verification / owner | Residual risk / authority |
|---|---|---|---|---|---|---|
| [SEC-n] | <named flow> | <attack and consequence> | <enforcement point> | <role> | <case, expected result, evidence> | <decision record or pending> |

Depth follows impact, exposure, privilege, data sensitivity and recoverability, not a fixed timebox or the number of boundaries. A single privileged endpoint may need extensive analysis. For AI tools, enforce path/action/data scope outside the prompt, constrain privileges and model untrusted inputs. Secrets and sensitive data must not leak into diagrams, test logs or error examples.

## Verification and review

At shape, planned checks and responsible owners are acceptable; at the required verification point, demand actual current evidence. Missing runtime evidence is unverified, not a passing security claim. Reviewer dimension 4 checks boundary → control → implementation → test/result → residual authority, including changed internal boundaries. Severity follows plausible impact and exposure; unresolved critical authorization/isolation risks block dependent work. Follow project red lines and existing risk-acceptance authority; the architect does not self-waive them.

Use the existing contract as the default output. Large projects may link a dedicated canonical model if already present or explicitly scoped in the packet; do not create duplicate security truth. Method background: [OWASP threat modeling process](https://community.owasp.org/Threat_Modeling_Process).
