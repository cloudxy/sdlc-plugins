# Debug dispatch and bookkeeping

The sole technical diagnosis method is [debug](../../debug/SKILL.md). Dispatch when a technical failure needs investigation, including the first occurrence; repeated technical rework must include a diagnosis record rather than a bare retry.

The manager sets `debug_protocol: <PLUGIN_ROOT>/skills/debug/SKILL.md`, cites the failure/artifact revision, grants scoped investigation access and names the task evidence path. Permit the debug companion through the registry when using companion_skills. Producer returns evidence, confirmed/suspected/unknown cause, eliminated hypotheses, mitigation/fix and verification limits. Record `root_cause` honestly (including `unverified: ...`) and follow normal retry/escalation limits.

Business scope or design-preference disagreement is an owner decision, not a command-reproduction exercise. Record that classification and decision in root_cause bookkeeping when a repeated rework gate requires a field; do not pretend it is a reproduced technical cause. For incidents, follow deliver's mitigation-first process. Review still uses the changed artifacts and current evidence independently.
