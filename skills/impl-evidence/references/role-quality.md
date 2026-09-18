# Professional review criteria

Read the section for the producing role during execution and independent review. These role-specific criteria were moved from agent identities; methods and self-checks remain in this skill.

## frontend

- Reads the **why** before the ticket: the key journey J-n, the chosen prototype screenshots, the signature moment, `design-system.md` tokens.
- Implements every designed state (empty, loading, error, boundary, permission, offline) with the designed copy; spacing, type and motion come from tokens; keyboard focus and contrast pass.
- Builds against the contract (mock allowed while the backend lands), then runs the slice **against the real API** and walks it like a user.
- Captures screenshots at the designed breakpoints, compares them with the prototype, and fixes the visible gaps before handing over — integration evidence in `03-impl/T-n-integration.md`.
- Evidence is command + exit code for build and tests, plus screenshots for behaviour.

## backend

- **Contract first**: example responses or a mock the frontend can build against on day one; a contract test that fails if the implementation drifts.
- Every operation decides its transaction boundary, idempotency and concurrency control; external calls stay outside transactions; errors map to contract codes, including the fallback branch.
- Server-side events from `01-define/tracking.md` are emitted with the agreed names and properties; logs carry trace ids, never secrets or unmasked PII.
- Self-test evidence (command + exit code) covers the four easily-missed cases: rollback, idempotency, concurrent writes, dependency failure.
- Joins the slice's integration run and fixes drift found there.

## algo

- An eval set built from real task samples (versioned, labelled, stratified like production) exists before any quality number.
- A no-AI or rules baseline is scored, so "better" means something.
- One variable per iteration, with a results table; latency, cost and quality trade-offs chosen explicitly.
- Primary → backup → rules fallback designed and tested; the user-facing failure moment designed with the designer.

## miner

- The action and the cost of each error are framed first (who acts on the score; precision vs recall trade-off).
- Features have as-of timestamps and come from tracking and warehouse layers with known definitions.
- Time-based splits, a rules baseline, lift / PR-AUC and calibration reported; segments that growth will use are registered in `data/tags.yaml` with refresh cadence and owner.
