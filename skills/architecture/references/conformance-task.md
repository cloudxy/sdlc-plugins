# Verify / conformance entry

Purpose: determine which accepted architecture obligations are met at the supplied implementation version. Feasibility and contract design have different inputs and remain separate tasks.

Start with the accepted contract version and its decision record, architecture baseline, source snapshot and explicit verification records. Match each obligation to source location, check identity, environment and outcome. Read lifecycle for ownership/status rules, quality-attributes for relevant measurable constraints, and threat-model when the change affects assets or trust boundaries. Do not load unrelated design methods just to fill a checklist.

Distinguish three claims: static code property, executed check on a source version, and behavior of an identified running build. An endpoint existing in code supports only the first. A passing check for another environment or an older source does not support the second. A screenshot or reachable URL without build association does not establish the third.

Example: the contract requires tenant isolation; a successful single-tenant test does not exercise cross-tenant denial. Inspect the filter and supplied check coverage. If access is available and execution is in scope, run the missing check and preserve its raw record; otherwise report the obligation unverified with its owner and affected consumers. Do not weaken the accepted tenant rule to make conformance pass.

Use the obligation table in lifecycle. Return met/deviation/unverified per obligation, concrete evidence limitations and proposed owner actions. Blocker/major items become immutable result judgments plus manager-maintained obligations; a separate resolution record closes them later. The report may be mechanically complete while obligations remain open. It does not approve its own exception, replace QA/QC, or prove release readiness.
