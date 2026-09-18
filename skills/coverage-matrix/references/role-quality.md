# Professional review criteria

Read the section for the producing role during execution and independent review. These role-specific criteria were moved from agent identities; methods and self-checks remain in this skill.

## qa

- **Risk-based strategy**: core journeys J-n are automated E2E on the running app (screenshots on failure); boundaries, permissions and state transitions are tested at the cheapest layer that proves them.
- **Exploratory testing** charters on the riskiest areas (new flows, money, permissions, concurrency) with session notes and the bugs they found.
- **Tracking validation**: each event EV-n fires once, at the right moment, with the agreed properties.
- A trace matrix with no silent holes: every FR, NFR, J-n and EV-n has a test or a reasoned exemption; hollow assertions are defects.
- Environment fidelity (production DB dialect, realistic data volume, real integrations or named mocks) — or the gap is escalated with a plan.
