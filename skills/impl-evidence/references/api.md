# Backend — contract to reliable implementation

Job: **turn contracts into implementations that are correct under concurrency, safe on failure, and debuggable in production**.

One discipline: **contracts are input, not suggestions.** If the contract has problems, go back to `architect`. Silently deviating means `frontend` built against the original contract and nothing will match.

| Task | Approach |
|---|---|
| **Implement a ticket (API endpoint)** | Full chain: read contract → map to layers → implement → self-test |
| **"Should this have a transaction?"** | Contract analysis: multi-table write? → yes. Single read? → no. See [references/concurrency-and-transactions.md](api/concurrency-and-transactions.md) |
| **"How to make this idempotent?"** | Unique constraint + upsert, or idempotency key |
| **"This list is slow, add Redis?"** | Find N+1 / missing JOIN first. Cache on an N+1 path hides the shape |
| **Debug a backend error** | Read logs → trace to layer → check contract → fix or escalate |

## Gotchas

- **async context calling `redis_client()` (sync) blocks the event loop.** Use `await get_async_redis()`. This caused backend freeze ([ESC from freeze pattern]).
- **`session.commit()` expires ORM objects.** Accessing attributes after commit triggers a synchronous refresh that crashes async code. Capture `int(obj.id)` before commit.
- **Service methods must have a logger at entry.** R10 red line: `logger = get_logger("service.<domain>")`. No logger = no evidence trail.
- **Router must not import ORM models.** ORM leaks into the API layer and serialization becomes unpredictable. Use Pydantic schemas at the boundary.
- **Don't write implementation matching your preferred style — match the existing codebase's style.** Two styles in one repo is worse than one imperfect style.

## Key decisions

### Contract-to-layer mapping

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

**Transaction:** multi-table write → transaction. Single read → no. If a partial write can leave inconsistent data → transaction. Read [references/concurrency-and-transactions.md](api/concurrency-and-transactions.md) for isolation levels and deadlock patterns.

**Idempotency:** retryable operations (payment, message processing) need idempotency. Implementation: unique constraint on business key + upsert, or idempotency key table with status tracking.

**Concurrency:** check for read-modify-write races. Optimistic locking (version column) for low contention; pessimistic (SELECT FOR UPDATE) for high contention. Read the reference for patterns.

### Slice discipline

- **Contract examples first**: for each endpoint in the slice, commit example request/response pairs (or an OpenAPI mock) before implementing internals; frontend builds against them in parallel.
- **Contract test**: a test that fails when the implementation's response shape or error codes drift from the contract.
- **Server-side events**: emit the `tracking.md` events whose source of truth is the database (orders, state changes, imports) after the transaction commits.
- **Join the integration run**: when frontend walks the slice on the real service, fix drift in the same ticket rather than opening a follow-up.

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | Ticket (`story-n.md`: FR anchors + boundaries + acceptance checklist) · API/event contracts (`architect`) · `schema.dbml` + `db-spec.md` (`dba`) · existing codebase conventions |
| **Output** | Implementation code · ORM models · migration execution records · self-test evidence (command + exit code) · ticket evidence section |
| **Downstream** | `qa` (testable API + known boundaries) · `architect` (contract issues found) · `frontend` (actual behavior vs contract, if different) |
| **Refuse** | Defining table fields · changing contracts · changing acceptance criteria · writing test cases |

**Three kinds of contract problems, three responses:**
- **Contract ambiguity** (error codes undefined, nullability unclear, idempotency semantics missing) → **back to `architect`**
- **Acceptance criteria unreachable** → **stop and escalate to `pm`**. Changing the standard is their authority.
- **Schema insufficient** (missing field/index) → back to `dba`, don't write your own migration.

## Self-check

- [ ] `pytest -q backend/tests` exit code 0?
- [ ] `check-arch.sh` zero violations?
- [ ] Code matches existing project patterns (not self-invented style)?
- [ ] Every story acceptance item has a corresponding implementation?
- [ ] Self-test evidence = command + exit code pasted verbatim?
- [ ] Contract deviations (if any) escalated, not silently absorbed?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [concurrency-and-transactions.md](api/concurrency-and-transactions.md) | Handling concurrent writes, deciding transaction boundaries, or debugging deadlocks |
| [layering-and-contracts.md](api/layering-and-contracts.md) | Router/Service/Repository boundaries, ORM leak, contract mapping |
| [auto-agents-pitfalls.md](api/auto-agents-pitfalls.md) | Verified auto_agents traps (code+test / ESC / gate only) |
| [templates/impl-evidence.md](../templates/impl-evidence.md) | Story evidence (command + exit code) |

> Gotchas based on: `anthropics/skills@41bbe19` (pdf SKILL.md IMPORTANT-warning pattern) · project incidents from auto_agents git history

