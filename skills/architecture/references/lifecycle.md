# Architecture task lifecycle

`workflow/registry.json` owns task identifiers, paths and product ownership. This reference owns architecture task behavior. Every return identifies input versions, decisions, consumers and evidence. `workflow.py check-task` checks minimum artifact presence; it neither approves a decision nor completes a whole stage.

## Baseline — product / bootstrap

Read the available code, canonical contracts, migrations, deployment records and measurements. Cite revision/environment/date. A deployment manifest proves declared configuration, not what is running. Mark inferred or inaccessible facts explicitly.

| State | Evidence required | Baseline treatment |
|---|---|---|
| proposed | Feature delta and unanswered decisions | Link under pending changes; never replace current topology |
| accepted | Decision owner and authorization record | Link accepted ADR and intended change; not proof of implementation |
| implemented | Code/build revision and relevant verification | Update implemented facts at that revision; deployment still unknown unless evidenced |
| deployed | Release/environment record and relevant operational verification | Update deployed facts for that environment |

Refresh when implementation, deployment, a failed check, incident or revisit trigger changes the evidence. A cancelled feature closes its pending delta; it never changes current facts. Keep normative goals/constraints separate from observed state. Return delta rows; the manager owns logs. Use the baseline template; do not duplicate feature contracts into it.

## Feasibility — define / feasibility

Use before freezing dependent PM/design choices when a material technical assumption is unresolved; it may also inform design exploration. Read the question, known business constraints and existing evidence. No completed spec or final prototype is required.

The feasibility artifact records:

| Field | Required content |
|---|---|
| Question | Falsifiable claim and which decision depends on it |
| Existing evidence | Versioned code, measurements or documentation; why insufficient/sufficient |
| Experiment | Environment, representative inputs, limits, resource budget, permitted side effects and stop condition |
| Observation | Commands, raw result paths, measurement limits; label estimates |
| Conclusion | supported / unsupported / inconclusive within the tested conditions |
| Next action | Decision owner, dependent artifacts and what remains blocked |

Inspect read-only evidence when enough. If an experiment is needed, list its code and logs explicitly in the packet, e.g. `01-define/spikes/<question>/`; use isolated test resources. Production mutations, credentials or paid provisioning require their own authority. Do not install a production implementation as a spike. If tools, access or time are missing, return inconclusive and the proposed experiment; do not invent results. A negative result proposes options to PM/design, not an automatic scope reduction.

## Contract — shape / contract

Consume the current baseline, approved business requirements and any feasibility results. UI work also consumes the approved final prototype source/version, flows, states, tokens and component IDs. Missing design inputs block the dependent UI portion, not unrelated feasibility work.

Write the smallest feature delta using the contract template. Declare each applicable output with path/version, owner and consumer: API/event contracts, ADRs, diagrams and complete slice tickets. Reuse existing canonical files by reference. The manager lists every new output in the packet and verifies every declared file, not just the registry's minimum `contract.md`. Return newly discovered output needs for packet revision; do not claim them complete without producing them.

For each consequential architecture obligation record its ID, source, expected outcome, check method/environment, implementer, verifier and due point. The architect can run existing checks and scoped experiments. Implementers own production check/CI code; QA independently verifies behavior; SRE verifies operational conditions. A planned fitness function is not a passing check.

A parent slice owns a complete consumer journey and names one `slice_integrator`. UI/API/schema/test subtasks can be separate assignments under it; all subtasks done does not close the slice until its real integration run. API/SDK/batch/native slices use the actual supported surface. Split large work into dependency-based waves, not a fixed FR count. A ticket table alone does not authorize implementation: each scheduled slice needs a complete ticket and accepted contracts.

## Change impact — shape / change-impact

Can be dispatched when a mismatch is discovered in any later stage. This task belongs to shape; dispatch does not automatically rewind global workflow state or authorize implementation changes.

1. Cite the current contract/spec versions, observed mismatch and reproduction evidence. Distinguish an implementation defect from a changed requirement or false architecture assumption.
2. List affected user behavior, invariants, risk, consumers, contract/design/data/ticket/test versions and proposed alternatives. Identify which existing decisions still authorize the change and which require a new owner decision.
3. If authorization is pending, keep the accepted contract unchanged and name blocked dependents. A completed impact report is not approval to proceed.
4. Once authorized, update only packet-authorized architecture files; route PM/design/DBA/data artifacts to their owners. Record old/new revisions, decision authority and revalidation actions. The manager marks affected artifacts/gates stale and schedules rework; unaffected work can continue.

## Conformance — verify / conformance

Use when the change adds or alters consequential boundaries, quality/security obligations or accepted architecture decisions, or implementation evidence indicates drift. Read accepted obligations, actual code/build revision and raw check records.

| Obligation ID/source | Expected behavior | Implementation revision | Evidence, run/environment | Observed result | Status | Owner/action |
|---|---|---|---|---|---|---|
| <ID/link> | <constraint> | <revision> | <raw record or missing> | <observation> | met / deviation / unverified | <rework or verification> |

Static inspection can establish a static property; it cannot prove runtime latency, isolation or recovery. Missing/stale evidence stays unverified. A required obligation with deviation/unverified prevents the manager from declaring architecture conformance satisfied; route it to the responsible owner for rework or an explicit authorized exception, then independent review. Do not silently waive it, approve your own business change or claim release readiness. Conformance supplements QA, design acceptance and QC; it does not replace them. Promote baseline facts only with the corresponding evidence and product write scope.
