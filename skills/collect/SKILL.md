---
name: "collect"
description: "Use this skill when the spawn packet names data-collector or collect, or $collect. Do NOT load in /sdlc or for warehouse ETL."
when_to_use: "Spawn packet names data-collector, companion_skills includes collect (pm writing tracking.md, qa validating events), or $collect. Do NOT use from parent /sdlc, warehouse ETL, or backend APIs."
---

# Collect — tracking plans first, then logs and external sources

Job: **capture the data the product needs correctly the first time.** Select the sources the product actually needs: external APIs/crawlers, business logs/CDC and/or user behaviour events. For external-data products, test source availability, fields and freshness before promising dependent product behavior. External collection does not require telemetry or a warehouse.

| Who loads it | Track | Deliverable | Template |
|---|---|---|---|
| pm (companion, `tracking: yes`) | Event requirements for this change | `01-define/tracking.md` | [templates/tracking.md](templates/tracking.md) |
| data-collector (`collect/tracking`) | Implementation design + proposed product tracking delta | `02-shape/collect/tracking-impl.md` · product `data/tracking-plan.yaml` | [templates/tracking-impl.md](templates/tracking-impl.md) · [templates/tracking-plan.yaml](templates/tracking-plan.yaml) |
| data-collector (`collect/source`) | New partner API / CDC / crawler | `02-shape/collect/data-source-analysis.md`; code only in the implement task | [templates/data-source-analysis.md](templates/data-source-analysis.md) |
| data-collector (`collect/implement`) | Implement approved event/source contracts: SDK, server events, source adapter — inside the packet's scoped `source_writes` | `03-impl/collect-evidence.md`: changed files, commands, samples, limitations | — |
| data-collector (`collect/validate`) | Correlate a known input through ingestion to the actual destination | `04-verify/collect-validation.md` | see [tracking-validation.md](references/tracking-validation.md) |
| qa (companion, verify) | Event validation rows EV-n | rows in `04-verify/coverage.md`, referencing collect-validation instead of copying it | see [tracking-validation.md](references/tracking-validation.md) |

## Gotchas

- **Events defined after launch cannot measure the launch.** Tracking is designed in define, implemented with the feature, validated in verify — never "补埋点" next sprint.
- **Names drift fastest.** `click_btn_2`, `ReportView`, `report_viewed` for one action → three metrics that never agree. One convention (`object_action`, past tense, snake_case) in the product tracking plan; new events reuse existing objects and properties.
- **Identity is a design decision.** Anonymous id → user id stitching at login/signup, cross-device, and logout must be decided up front, or funnels break at registration.
- **Client events lie under ad blockers, retries and offline queues.** Money, orders and state changes are server-side events; client events are for UI behaviour.
- **PII does not belong in event properties.** No phone numbers, emails, ids of third parties in clear text; consent state is itself a property or a gate.
- **Every event serves a metric.** An event with no metric id in `data/metrics.yaml` (or a named analysis) is noise — do not add it.
- **Design completion is not collection completion.** A design document proves nothing about delivery: distinguish request emitted, accepted, persisted and queryable. A mock-only run does not prove destination delivery. Frontend/backend own their code; do not claim their changes from a design document.
- **Transport may be at-least-once.** Validate the specified downstream deduplication boundary rather than promising exactly-once delivery. Alert thresholds depend on expected traffic and freshness, not universal event counts.
- **Crawlers are their own subsystem.** They never import the application backend; choose an ingestion boundary appropriate to scale (an API, controlled batch or queue) with idempotent keys and explicit ownership; rate limits and the source's access contract are respected; repeated zero-item runs raise an alert. SQLite accepts PostgreSQL-only syntax such as `NULLS LAST` that MySQL rejects — test on the production dialect.
- **Staging is not landed.** Between collector-side staging and consumer-side sync, keep an explicit cursor (an `unsynced` set or equivalent) and maintain it when deleting partial data. Before claiming collection complete, state which segment the data reached — the crawler analogue of emitted ≠ persisted.
- **Classify failures and recovery conditions.** Separate task errors, structural changes, access/session restrictions and resource faults using observed evidence. Preserve task ownership; select retry, pause, dead-letter or recovery within the affected scope. Fixed next-day pauses and requeueing are project policies, not defaults. Do not repeatedly replay an action that cannot repair the fault.
- **Shared dependencies determine failure scope.** Stop all operations sharing a failed account/session or a required quota ledger; keep independent healthy sources runnable. Do not switch types to bypass a shared stop. Browser closure, bounded login recovery and scheduler waiting are separate lifecycle decisions. Noncritical telemetry can degrade without a collection-wide stop.
- **Ownership survives failure.** Define claim/expiry/requeue handoff and the authority to commit; atomic pop alone does not close the claim-to-pending gap. For persistent or segmented collection use [collection-recovery.md](references/collection-recovery.md) for business checkpoints, completion conditions, proactive budgets and recoverable delivery.
- **Versioned captures are the contract of record.** Validate every routing/attribution assumption against real request+response captures, not memory or page bundles; a guard added "for hygiene" that rejects all valid payloads (substring month check vs millisecond timestamps) is worse than no guard — test guards in both directions with captures. Keep a real-capture regression set and run every parser change through it. When identity (geo id, date key) lives only in the request payload, extraction cannot recover it from the response — inject it, or the data is unattributable.
- **Confirmed-empty is a delivery state.** A success shell with an empty list must be persisted as evidence (`data: []`) and downstream consumers must accept and retire empty batches; collapsing empty with missing turns a legitimately empty module into an infinite recollect loop and makes "no data" indistinguishable from "not collected".
- **Additive metrics are free end-to-end pipeline checks.** Where parts sum to a whole (Σ city rows == province row exactly), cross-sum before declaring the pipeline healthy; non-additive metrics that legitimately disagree make the contrast informative.

## Excellence bar

| Excellent | Reject as mediocre |
|---|---|
| Each event: name by convention, trigger moment defined from the user's point of view, client/server placement, typed properties with allowed values, the metric id it feeds, owner | "加个点击埋点" |
| Identity, session and consent rules written once in the product plan and referenced | Each feature invents its own user id field |
| Validation steps per event that qa can run (network capture, debug view, warehouse query) | "上线后看看有没有数据" |
| External source: rate limits, retries, schema checks, legal/ToS review, freshness SLA, zero-data alert | A spider that works on the author's laptop |

## Steps

### Track: tracking requirements (pm, `01-define/tracking.md`)

1. From the spec's metrics blueprint, list each metric that needs new data.
2. Design events with [event-design.md](references/event-design.md): reuse objects and properties from the product `data/tracking-plan.yaml` first.
3. Number events `EV-n`; tie each to a journey step `J-n` and a metric id. Write `01-define/tracking.md`.

### Track: implementation design (data-collector, `collect/tracking`)

1. Propose the feature's event delta against product `data/tracking-plan.yaml`; publish approved definitions with status/version, never label an unimplemented event as live. Apply the delta to the canonical product file only within packet ownership (conventions, identity, common properties stay consistent).
2. Decide placement (client SDK / server / both), batching, offline behaviour, sampling, consent gating.
3. Write validation steps per event ([tracking-validation.md](references/tracking-validation.md)) and post-launch data-quality monitors.
4. Write `02-shape/collect/tracking-impl.md`; record the product-layer delta.

### Track: external sources (`collect/source`)

1. Analyse the source with [templates/data-source-analysis.md](templates/data-source-analysis.md): type (API / HTML / RSS / CDC), scope, rate limits, ToS and legal review, freshness need, schema.
2. Partner APIs and CDC: retries with backoff, idempotent ingestion keys, schema validation at ingestion, lag monitoring.
3. Crawlers: follow [scrapy-redis-distributed.md](references/scrapy-redis-distributed.md) and [anti-scraping-playbook.md](references/anti-scraping-playbook.md); when blocked, diagnose with [anti-scraping-escalation.md](references/anti-scraping-escalation.md) and respect the source access contract; use supported APIs, backoff and owner escalation when access is blocked. These stack-specific references are optional, not a requirement for every source. Start from [templates/spider-template.py](templates/spider-template.py), [templates/spider-config.py](templates/spider-config.py) and [templates/item-definition.py](templates/item-definition.py).

### Track: implement and validate (`collect/implement`, `collect/validate`)

1. Implement only approved contracts, inside `source_writes`; record changed files, commands, samples and limitations in `03-impl/collect-evidence.md`.
2. Validate end to end: a known input through ingestion to the real destination; check retries/deduplication, missing and late events, identity and consent where applicable. Record environment, source version and sample IDs in `04-verify/collect-validation.md`.

The product tracking plan is the unique event-definition source; feature requirements, implementation notes and validation reports reference event IDs and its version. Proposed, accepted, implemented and validated are distinct statuses.

## Self-check

- [ ] Every event has name, trigger, placement, typed properties, metric id and owner?
- [ ] Names and properties reuse the product tracking plan conventions?
- [ ] Identity stitching, consent and PII rules referenced, not reinvented?
- [ ] Validation steps exist for every EV-n, and qa's matrix can reference them?
- [ ] Product `data/tracking-plan.yaml` updated and the delta recorded (with the right status)?
- [ ] External sources: rate limit, ToS/legal, classified retries, staging-to-landed cursor, schema checks, zero-data alert?
- [ ] Implement/validate: evidence distinguishes emitted, accepted, persisted and queryable; no mock-only claim of delivery?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [event-design.md](references/event-design.md) | Naming events, properties, identity, client vs server, sampling, consent |
| [tracking-validation.md](references/tracking-validation.md) | Writing validation steps, qa verifying EV-n, post-launch data-quality monitors |
| [collection-recovery.md](references/collection-recovery.md) | Persistent tasks, business checkpoints, shared failures, budgets or asynchronous delivery |
| [scrapy-redis-distributed.md](references/scrapy-redis-distributed.md) | Building or debugging a distributed crawler |
| [anti-scraping-playbook.md](references/anti-scraping-playbook.md) | Assessing a new target site, designing countermeasures |
| [anti-scraping-escalation.md](references/anti-scraping-escalation.md) | 403 / 429 / captcha / empty responses |
| [templates/tracking-plan.yaml](templates/tracking-plan.yaml) | Bootstrapping or extending the product tracking plan |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
