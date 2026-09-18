---
name: "architecture"
description: "Use when shaping architecture (scenarios, options, ADRs, contracts, tickets). In sdlc-workflow:architect or $architecture. Do NOT use while /sdlc runs or for schemas."
when_to_use: "Use when defining quality attribute scenarios, candidate architectures, module boundaries, ADRs, API contracts, or ticket decomposition. Load inside sdlc-workflow:architect. Do NOT use while /sdlc is running in this window. Do NOT use for implementation code or table schemas."
---

# Architecture — scenarios, options, boundaries, contracts, slices

Job: **choose the structure that meets this product's quality goals today and can evolve to the next stage — and make it executable as journey-slice tickets.** Good architecture is a set of trade-offs made on purpose against measurable scenarios, not a diagram.

| Task | Approach |
|---|---|
| **New feature (v4 shape)** | Read product `architecture.md` + picked design direction → quality scenarios + capacity → ≥2 candidate options → decision + ADRs → boundaries → contracts → vertical-slice tickets → write back `architecture.md` |
| **Product layer missing** | Reverse-engineer `architecture.md` from code, deploy files and dashboards ([templates/architecture-baseline.md](templates/architecture-baseline.md)); mark inferences `[推断]` |
| **Technology selection** | Options with evidence → ADR with rejected alternatives → decision + revisit trigger |
| **Integrate team outputs** | Consistency check (names / tables / keys / events across spec, contract, db-spec, tracking) → resolve conflicts |
| **"Too big to estimate"** | Boundary derivation → module split → per-slice tickets |

## Gotchas

- **Adjectives are not requirements.** "High performance", "scalable", "secure" decide nothing. Turn each into a quality attribute scenario with a measure (stimulus → environment → response → measure) before comparing options.
- **One option is not a decision.** Compare at least two feasible options against the scenarios; a straw man does not count. Record what was rejected and why, with evidence.
- **Feasibility pre-check is not drawing a diagram.** Read the existing code, run a spike, or query a table. List stores already in the topology before choosing a brand.
- **Scheduling state is two facts.** Enqueue / lease / lock is coordination; task definition / final state / audit is record. A single-brand answer (Redis vs MySQL) to a compound noun is a false binary. Reusing an existing Redis for coordination is not "a second store"; the real bar is **two writers for the same fact**. Details: [adr-and-tradeoffs.md](references/adr-and-tradeoffs.md) §2.
- **Capacity comes from the product, not from habit.** Estimate peak QPS and data growth from DAU, per-user actions and peak factor in the product layer; say which scenario breaks first and at what trigger.
- **Horizontal tickets pass while journeys fail.** "Tables", "APIs" and "pages" as separate tickets can all be done while no user can complete the journey. Slice along journey steps, each ticket demonstrable end-to-end.
- **"We'll decide later" is tech debt.** Either decide (ADR) or name a rabbit hole with a revisit trigger.
- **Every ticket anchors to an FR and a journey step.** Unanchored tickets cannot be verified.
- **Destructive changes carry expand-contract steps** in the ticket, or they ship as one-step breaks.
- **Architecture rots without checks.** Boundaries and budgets that matter become fitness functions CI can run.
- **Program-sized shape overflows one session.** If frozen FR count > 20, this spawn writes `contract.md` + ADRs + the ticket **table**; a follow-up spawn writes `tickets/T-nn.md`.

## Excellence bar

| Excellent | Reject as mediocre |
|---|---|
| Quality scenarios with numbers, tied to NFRs and the capacity model | "系统需要高性能高可用" |
| ≥2 real options in a trade-off matrix; decision, rejected reasons, revisit trigger | One option described in detail |
| Evolution path: what changes at stage 2, triggered by what observable signal | Silent on growth, or premature microservices |
| Contracts with error codes, idempotency, pagination, versioning; data semantics handed to dba | Endpoint list without failure semantics |
| Journey-slice tickets, each demonstrable on the running product | Layer-by-layer tickets |
| Fitness functions (boundary / latency / dependency checks) wired to CI | Boundaries only in prose |

## Key decisions

### Quality attribute scenarios and capacity

For each relevant attribute (performance, scalability, availability, security, modifiability, cost, observability): source · stimulus · environment · response · measure ([quality-attributes.md](references/quality-attributes.md) §1–2 has a scenario catalog and a worked capacity estimate). Reuse `QAS-n` from product `architecture.md`; new scenarios get ids and are written back. Capacity: `peak QPS = DAU × requests/user/day ÷ 86400 × peak factor`; storage growth from records/day × size × retention.

### Candidate options and decision

Compare options on scenario fit (with spike or measured evidence), build cost, operational cost (new dependencies, failure modes, monitoring), evolvability, risk. Irreversible choices get an ADR ([templates/adr.md](templates/adr.md)); every ADR names rejected alternatives with evidence (the body must say **rejected** / **否决**) and a revisit trigger.

### Boundary derivation (from FRs to modules)

Cluster FRs by shared data model → shared lifecycle → shared ownership; test each candidate with: who calls it, what it owns exclusively, what breaks if it is rewritten. Dependencies single-direction; cycles mean the boundary is wrong ([boundary-derivation.md](references/boundary-derivation.md)). Default to a well-bounded monolith; split services only on independent scaling, release cadence, stack, team or fault-isolation signals.

### Evolution and fitness functions

Write the next stage (trigger → change → cost) into product `architecture.md`. Turn load-bearing rules into checks: import boundaries, P95 budgets on core journeys, forbidden dependencies, migration reversibility.

### Journey-slice tickets

One ticket = one journey step range, backend + frontend + tests + integration run, with the demonstrable outcome written in the ticket ([templates/story.md](templates/story.md)). Backend publishes contract examples first so frontend can build in parallel.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | spec (FR/NFR, journeys J-n) · picked design direction + flows (ui: yes) · product `architecture.md`, `domain-model.md`, `strategy.md` (scale assumptions) · existing codebase |
| **Output** | `02-shape/contract.md` ([templates/contract.md](templates/contract.md): scenarios, options, boundaries, contracts, slices, `[SEC-n]`) · `adr-*.md` · `contracts/` ([templates/api-contract.md](templates/api-contract.md)) · tickets · product `architecture.md` update + delta rows returned to the manager |
| **Downstream** | dba (data semantics) · implementers (slices + contracts) · qa (risks, journeys) · sre (topology, capacity) |
| **Refuse** | Implementation code · schema-level design · product picks (prepare options; humans decide product) |

## Self-check

- [ ] Quality attribute scenarios with measures, linked to NFRs; capacity estimated when traffic or data grows?
- [ ] ≥2 real options compared; decision with rejected reasons (rejected / 否决) and revisit trigger?
- [ ] Module boundaries single-direction; storage ADRs split facts (coordination vs record)?
- [ ] Contracts define errors, idempotency, pagination, versioning; data semantics handed to dba?
- [ ] Tickets are journey slices with FR + J anchors and a demonstrable outcome?
- [ ] Destructive changes note expand-contract steps; feasibility checked for the riskiest assumption?
- [ ] Q-security = yes ⇒ contract has `[SEC-n]` (boundary → mitigation → NFR / qa)?
- [ ] Evolution path and fitness functions updated in product `architecture.md`; delta row returned?
- [ ] Named output paths exist on disk?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [quality-attributes.md](references/quality-attributes.md) | Writing scenarios, estimating capacity, comparing options, planning evolution stages, choosing fitness functions |
| [adr-and-tradeoffs.md](references/adr-and-tradeoffs.md) | Writing ADRs, storage and consistency trade-offs, sync vs async |
| [boundary-derivation.md](references/boundary-derivation.md) | Deriving module boundaries from FRs, fixing cycles, when to split services |
| [contract-design.md](references/contract-design.md) | API and event contracts |
| [threat-model.md](references/threat-model.md) | Q-security = yes: STRIDE per trust boundary → `[SEC-n]` in the contract |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified auto_agents boundary traps |
| [templates/architecture-baseline.md](templates/architecture-baseline.md) | Bootstrapping or updating product `architecture.md` |
| [templates/contract.md](templates/contract.md) · [templates/adr.md](templates/adr.md) · [templates/story.md](templates/story.md) · [templates/api-contract.md](templates/api-contract.md) | Writing the deliverables |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
