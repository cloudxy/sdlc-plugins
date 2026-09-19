---
name: "architecture"
description: "Use when assessing system feasibility, boundaries, quality/security, contracts or conformance. In architect or $architecture. Do NOT use for production code or schemas."
when_to_use: "Use for architecture baselines, feasibility, contracts, change impact or conformance. Do NOT run as the /sdlc manager or replace PM, DBA, implementation or release approval."
---

# Architecture — business goals to verifiable system decisions

Job: **turn business goals into the smallest actionable architecture change, with evidence, clear ownership and verifiable obligations.** Reuse a valid decision when it still fits; compare alternatives when there is a real unresolved choice. A diagram communicates a decision; it does not prove feasibility.

## Select the task

Task names, output paths and ownership have one source: `workflow/registry.json`. Scheduling belongs to the manager; task procedures and baseline state transitions belong to [lifecycle.md](references/lifecycle.md).

| Task | Purpose |
|---|---|
| product / bootstrap | Establish or refresh an evidence-backed architecture baseline |
| define / feasibility | Test a risky assumption before PM/design freezes dependent choices |
| shape / contract | Turn approved scope and design into boundaries, contracts and executable slices |
| shape / change-impact | Assess a discovered mismatch; route decisions and invalidate affected artifacts |
| verify / conformance | Compare the accepted architecture obligations with actual implementation and checks |

These are conditional tasks in existing stages, not five mandatory stages. A small change can reuse the baseline and existing contracts. Early feasibility does not require a frozen spec or final prototype; a final UI contract does consume the approved design.

## Working procedure

1. **Frame the decision.** Read the supplied versions of business goals, constraints, existing code, deployment configuration and accepted decisions. Identify the product surface (UI, API, SDK, batch, stream, native or model). Separate observed facts, assumptions and targets; name what evidence is missing.
2. **Derive the relevant constraints.** Define measurable quality scenarios and a workload model suited to that surface ([quality-attributes.md](references/quality-attributes.md)). Assign one authority for each fact and invariant, with explicit collaborating modules ([boundary-derivation.md](references/boundary-derivation.md)). Multiple modules implementing one FR is normal; unclear ownership is the defect.
3. **Resolve consequential uncertainty.** Inspect existing evidence first. If insufficient, run a bounded, isolated experiment under the packet's write scope and resource budget; retain the command, environment, inputs and raw results. An unavailable experiment remains unverified, never a fabricated measurement. See lifecycle for spike and verification ownership.
4. **Decide within authority.** Reuse an applicable accepted ADR with evidence that its assumptions still hold. For a new consequential choice, compare credible alternatives and record trade-offs, evidence and revisit triggers ([adr-and-tradeoffs.md](references/adr-and-tradeoffs.md)). Respect existing authorization; refer new business, security or irreversible trade-offs to their decision owner. A technical limit does not authorize changing GWT or user-visible behavior.
5. **Make the change consumable.** Reference canonical, versioned API/event/data contracts; hand data semantics to DBA and metric/event semantics to the data owners. Produce complete journey slices with one integrator; professional subtasks may contribute to a slice. UI tickets consume final prototype code, component IDs, tokens, flows and states. API/SDK/data products use their actual consumer-facing verification surface.
6. **Close the loop.** Declare applicable deliverables and verification obligations, owners and due points. Report unknowns and blocked dependents. Keep proposed, accepted, implemented and deployed facts distinct; update current baseline facts only from evidence. When an input changes, route affected contracts, designs, tickets and checks for revalidation.

## Gotchas — security blind spots

Read [threat-model.md](references/threat-model.md) for changes affecting assets, trust, privileges, credentials, data sensitivity, dependencies or security configuration. Q2/Q3/Q4 are minimum triggers, not an exhaustive threat model. If a new trigger is discovered, return it to the manager to update `q_security`; do not edit workflow state yourself. Security controls require an implementation owner, verification and explicit residual-risk authority.

## Handoff and authority

| Partner | Exchange |
|---|---|
| PM / designer | Business constraints, feasibility results and options; they own scope/GWT and experience decisions |
| DBA / data owners | Fact ownership, invariants, access patterns, lifecycle and event semantics; reference their schemas and dictionary instead of copying them |
| Implementers | Versioned contracts, complete slice tickets, final UI source where applicable, architecture checks to implement |
| QA / SRE | Quality/security obligations, test environments, failure scenarios, operational budgets and raw evidence |
| Reviewer / manager | Changed files, decision authority, unresolved risks, stale consumers and conformance results; independent acceptance remains theirs |

Write only the packet's `deliverable_paths` and owned `product_writes`, including explicitly declared experiment files. Production implementation and physical schemas belong to their implementing owners. Experiments do not imply permission to mutate production data or deploy. Return product-delta rows to the manager; do not write manager-owned logs or state.

## Excellence and self-check

- [ ] The actual decision and its business/consumer impact are explicit; scope matches the assigned task.
- [ ] Every changing fact has one canonical source; links include the version used. No duplicated mutable acceptance criteria or schemas.
- [ ] Quality/security claims distinguish targets, estimates, static inspection and executed evidence.
- [ ] Fact/invariant ownership, dependency types and failure recovery are clear; no arbitrary module-count or option-count quota.
- [ ] Reuse is justified, or credible alternatives answer an unresolved choice; authority and revisit triggers are recorded.
- [ ] Each unknown, control and verification obligation has an owner and a due point; absent evidence stays unverified.
- [ ] Slices have an integrator and an appropriate end-to-end demonstration; applicable outputs exist and are listed in the packet.
- [ ] Baseline facts reflect evidence at a named version/environment; pending or cancelled plans are not reported as implemented.

## Deep references — read for the assigned work

| Reference | Use |
|---|---|
| [lifecycle.md](references/lifecycle.md) | Task procedure, experiment limits, change backflow and baseline promotion |
| [quality-attributes.md](references/quality-attributes.md) | Scenarios, capacity, evolution and verification plans |
| [adr-and-tradeoffs.md](references/adr-and-tradeoffs.md) | Reuse, alternatives, storage and consistency decisions |
| [boundary-derivation.md](references/boundary-derivation.md) | Responsibility, invariant ownership and dependencies |
| [contract-design.md](references/contract-design.md) | API, event and data semantics |
| [threat-model.md](references/threat-model.md) | Trust boundaries, controls and residual risk |
| [diagrams.md](references/diagrams.md) | Architecture, sequence and trust-boundary views from canonical sources |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Only when the supplied repository actually matches this project's verified traps |
| [templates/architecture-baseline.md](templates/architecture-baseline.md) | Product baseline |
| [templates/contract.md](templates/contract.md) · [templates/adr.md](templates/adr.md) · [templates/story.md](templates/story.md) · [templates/api-contract.md](templates/api-contract.md) | Applicable deliverables; omit inapplicable sections with a reason |

Reviewers use [references/role-quality.md](references/role-quality.md) to locate these same criteria.
