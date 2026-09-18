# Professional review criteria

Read the section for the producing role during execution and independent review. These role-specific criteria were moved from agent identities; methods and self-checks remain in this skill.

## architect

- **Quality attribute scenarios** with numbers drive the design: latency, peak QPS estimated from DAU and peak factor, availability, data growth, cost, security, modifiability — tied to the product layer's assumptions.
- **2–3 candidate architectures** compared in a trade-off matrix against those scenarios; the decision records what was rejected, why, and the trigger to revisit.
- Boundaries follow capabilities and the domain model; dependencies are acyclic; contracts define error codes, idempotency, pagination, versioning.
- An **evolution path** (stage 1 → stage 2 when trigger X fires) and **fitness functions** (rules CI can check) keep the architecture from rotting.
- **Tickets are vertical slices** along key journeys — each verifiable end-to-end — not layer-by-layer chores.
- Feasibility is proven by reading code or a spike with numbers, not by drawing diagrams.
