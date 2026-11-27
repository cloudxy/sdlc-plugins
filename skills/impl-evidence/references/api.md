# Backend — contract to reliable implementation

Job: **turn contracts into implementations that are correct under concurrency, safe on failure, and debuggable in production**.

One discipline: **contracts are input, not suggestions.** If the contract has problems, go back to `architect`. Silently deviating means `frontend` built against the original contract and nothing will match.

| Task | Approach |
|---|---|
| **Implement a ticket (API endpoint)** | Full chain: read contract → map to layers → implement → self-test |
| **"Should this have a transaction?"** | Contract analysis: multi-table write? → yes. Reads can also require a transaction/snapshot when consistency demands it. See [references/concurrency-and-transactions.md](api/concurrency-and-transactions.md) |
| **"How to make this idempotent?"** | Unique constraint + upsert, or idempotency key |
| **"This list is slow, add Redis?"** | Find N+1 / missing JOIN first. Cache on an N+1 path hides the shape |
| **Debug a backend error** | Read logs → trace to layer → check contract → fix or escalate |

## Gotchas — inspect applicability

Check the installed stack and the project's conventions before applying a rule; these are verified lessons, not requirements for every API project. Tests and contract/concurrency regressions are within backend implementation responsibility.

- **Never block the event loop.** In async code a synchronous client call (cache, DB, HTTP) on a hot path stalls every request; use the async client. Confirm the actual client behavior and runtime before changing it.
- **ORM sessions that expire objects on commit bite async code.** Reading attributes after commit can trigger a synchronous refresh that crashes; capture ids or project to DTOs before commit.
- **For tenant-scoped requests, a missing tenant is an error.** Do not reinterpret NULL as global access. Explicit platform operations need their own accepted authorization boundary and isolation tests.
- **Log at service entry when the project requires it.** Follow the project's logging convention; no log = no evidence trail.
- **When the project adopts Router/Service/Repository separation, keep ORM models behind that boundary.** Use its established transport schemas (Pydantic only where installed); verify serialization and ownership against the accepted architecture.
- **Don't write implementation matching your preferred style — match the existing codebase's style.** Two styles in one repo is worse than one imperfect style.
- **Extraction returns three states: missing field ≠ empty collection.** `get(field, [])` collapses them; empty is valid evidence to persist and pass downstream (distinguishing "no data" from "not collected"), missing/malformed is a contract alarm to surface as `None`. Collapsing the two turns one end of the pipe into an infinite retry and the other into silent gaps.
- **Merge/dedup keys must cover the request's full identity.** When many responses share metric names and scopes (N geo units × same metric × same window), keying on the visible fields silently collapses N payloads into 1 — no error, no alert, data just shrinks. Composite keys (identity + metric), plus a regression case with N same-shaped payloads.
- **Every silent skip is an undiagnosable production hole.** Each drop path (unmatched shape, non-success shell, missing field, attribution mismatch) logs its reason at visible level; a later "some types never arrive" incident is only answerable from those lines. Diagnostic state at info, not debug.
- **Validate defensive guards in both directions against real traffic.** A hygiene check that rejects 100% of valid payloads (substring date match against millisecond timestamps) is worse than no check — the guard becomes the outage. Prove it passes captured valid payloads and blocks captured invalid ones; normalize formats (timezone, compact vs dashed dates) explicitly instead of matching literals.
- **Retry budgets are for transient causes; pair permanent failure with terminal handling.** A clear-and-recollect retry loop against a permanent condition (a legitimately empty module) never converges and burns quota; classify the failure first, and let the terminal path carry a distinct signal so schedulers treat it globally instead of cycling.
- **Keep backend processes strictly stateless across workers and replicas.** Never hold mutable session state, job progress, rate-limit counters, permission caches, uncommitted staging buffers, or cross-request coordination locks (`threading.RLock` / `asyncio.Lock` treated as global exclusion) in module globals, class attributes, or uncoordinated local tempfiles; persist shared state in the accepted DB or governed Redis keys.
- **Separate pure Functional Core from Imperative Shell, and enforce strict CQS.** Extract non-trivial pricing, allocation, state-transition, and visibility/permission rules into pure deterministic functions (explicit data snapshot + injected clock, zero DB/HTTP/file I/O) orchestrated by a thin `Service` shell. Queries (`GET`, `HEAD`, list/count, preview, readiness probe) must be strictly side-effect-free and zero-billing (CQS).
- **Stage shared dynamic visibility predicates once per request (DIE/SSOT).** When one response's `total`, facets, and `items` share a time- or state-dependent visibility predicate (latest row, expiry, rights, available media), materialize that visible set once inside the transaction and read all three from it (applying dimension filters afterward so sibling facets stay selectable), never re-running per-row `EXISTS` across statements, pulling the full set into process memory, or inventing summary tables/indexes from `backend`. Canonical specification and measurement rules live in [modeling-patterns.md](../../schema/references/modeling-patterns.md) §8.
- **When an endpoint adds a derived or transformed operation that a downstream consumer will read again, that artifact must inherit lineage and rights allowlists.** Register the operation (for example layer separation, composition, stitching, clip/remake) in the lineage and rights resolver, and verify with an integration test that feeds the derived output back into a downstream consumer; otherwise derived items default to unknown rights and fail downstream with 422.
- **Verify cold-start imports in a clean subprocess.** Adding or splitting modules can introduce circular imports hidden by warm test-collection order. Import the changed entry module directly in a fresh interpreter before reporting done.
- **When a catalog or provider sync manages items the user can turn off by hand, that sync must never overwrite explicit user disables.** Keep "disabled by system channel switch" and "manually disabled by user" as distinct states so periodic model/provider sync does not silently re-enable models the user turned off or break an active provider channel.

## Key decisions

### Contract-to-layer mapping

The following mapping applies to projects that explicitly adopt this layered Python service convention. For another stack or architecture, map the same contract obligations to its accepted boundaries; do not add Repository or Pydantic merely to match this table.

| Contract element | Layer | Note |
|---|---|---|
| Path / method / status code | Router | Protocol conversion only, no business logic |
| Request field validation | Schema (Pydantic) | Declarative, not in service |
| Permission check | Router or Service entry | Data-scope filtering is business logic → Service |
| Business rules / state transitions | Service | The ONLY home for business logic |
| Data read/write | Repository | Service doesn't construct ORM queries directly |
| Error code mapping | Unified exception handler | Business exception → contract `code` |
| Idempotency | Service + unique constraint | See below |
| Pagination | Repository + Schema | Limit validation in Schema |

### Transaction, idempotency, concurrency

**Transaction:** multi-table write → transaction. Read consistency may also need a transaction/snapshot. If a partial write can leave inconsistent data → transaction. Read [references/concurrency-and-transactions.md](api/concurrency-and-transactions.md) for isolation levels and deadlock patterns.

**Idempotency:** retryable operations (payment, message processing) need idempotency. Implementation: unique constraint on business key + upsert, or idempotency key table with status tracking.

**Concurrency:** check for read-modify-write races. Optimistic locking (version column) for low contention; pessimistic (SELECT FOR UPDATE) for high contention. Read the reference for patterns.

### Contract-driven exit criteria & slice discipline

- **Contract examples first**: for each endpoint in the slice, commit example request/response pairs (or an OpenAPI/JSON Schema spec) before implementing internals so `frontend` generates types and mocks in parallel.
- **100% LLD error-classification fidelity**: implement 100% of LLD error classifications returning the exact contract `code`s and HTTP statuses — never collapse distinct domain errors into generic `500`/`400` or invent undocumented error strings.
- **Executable contract tests before `qa` handoff**: run executable contract tests (`exit: 0`) verifying response shape, HTTP status codes, field nullability, and error envelopes against the locked contract before handing off to `qa`.
- **LLD resilience paths — zero silent omissions**: implement every LLD retry (bounded + jittered), circuit-breaker, and fallback/brownout path; if any resilience path is intentionally deferred in this slice, explicitly record `本次不实现（原因+授权）` naming the authorizing role (`architect` / `pm`) in [templates/impl-evidence.md](../templates/impl-evidence.md) — silent omission is a blocking defect.
- **Server-side events**: emit the `tracking.md` events whose source of truth is the database (orders, state changes, imports) after the transaction commits.
- **Join the integration run**: when `frontend` walks the slice on the real service, fix drift in the same ticket rather than opening a follow-up.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Ticket (`story-n.md`: FR anchors + boundaries + acceptance checklist) · API/event contracts (`architect`) · `schema.dbml` + `db-spec.md` (`dba`) · existing codebase conventions |
| **Output** | Implementation code · ORM models · migration execution records · executable contract-test & targeted self-test evidence (command + exit code) · resilience or `本次不实现（原因+授权）` declaration · ticket evidence section |
| **Downstream** | `qa` (testable API + passing contract tests + known boundaries) · `architect` (contract issues found) · `frontend` (locked contract + examples) |
| **Refuse** | Defining table fields · changing contracts · changing acceptance criteria ; implementer tests are required where applicable (QA remains independent) |

**Three kinds of contract problems, three responses:**
- **Contract ambiguity** (error codes undefined, nullability unclear, idempotency semantics missing) → **back to `architect`**
- **Acceptance criteria unreachable** → **stop and escalate to `pm`**. Changing the standard is their authority.
- **Schema insufficient or destructive DDL needed** → back to `dba` (`dba/migration` owns all destructive/expand-contract/shared-table changes; routine additive slice-local tables must match `schema.dbml` + ORM metadata + package manifest 1:1 per [industry-delivery-sops.md](industry-delivery-sops.md), never unilateral migrations).

## Self-check

- [ ] 100% of LLD error classifications implemented and returning exact contract `code`s?
- [ ] Executable contract tests verifying response shape, HTTP status, nullability, and error envelopes pass (`exit: 0`) before `qa` handoff?
- [ ] LLD retry / circuit-breaker / fallback paths implemented OR explicitly recorded as `本次不实现（原因+授权）` in `impl-evidence.md` (zero silent omissions)?
- [ ] Targeted tests for the affected module, contract and callers pass (full-suite test runs prohibited unless explicitly requested)?
- [ ] Applicable project architecture checks pass?
- [ ] Code matches existing project patterns (not self-invented style)?
- [ ] Every story acceptance item has a corresponding implementation?
- [ ] Self-test evidence = command + exit code pasted verbatim?
- [ ] Contract deviations (if any) escalated, not silently absorbed?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [concurrency-and-transactions.md](api/concurrency-and-transactions.md) | Handling concurrent writes, deciding transaction boundaries, or debugging deadlocks |
| [layering-and-contracts.md](api/layering-and-contracts.md) | Router/Service/Repository boundaries, ORM leak, contract mapping |
| [provider-authorization.md](api/provider-authorization.md) | API Key/subscription/CLI integration, readiness claims, channel dispatch, diagnostic and output boundaries |
| [templates/impl-evidence.md](../templates/impl-evidence.md) | Story evidence (command + exit code) |

> Historical project incidents remain in the maintainer archive; this procedure states their applicability without treating one project as the default.
