# Professional review criteria

Read the section for the producing role during execution and independent review. These role-specific criteria were moved from agent identities; methods and self-checks remain in this skill.

## sre

- Rollback path exercised in a real environment (code, data, config), with the window and data-compatibility limits written down.
- Canary plan with promotion/rollback thresholds that include the product guardrail metrics, not only error rates.
- Alerts carry runbooks (who, what to check first, escalation); dashboards exist before launch.
- Capacity checked against the quality scenarios in `architecture.md` and the traffic growth plans in `06-deliver/launch.md` — no campaign goes out before the system is stable.
- Secrets and environment config live outside the codebase; environment drift is documented.
