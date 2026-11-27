---
name: "collect"
description: "Use this skill when the spawn packet names data-collector or collect, or $collect. Do NOT load in /sdlc or for warehouse ETL."
when_to_use: "Spawn packet names data-collector, companion_skills includes collect (pm writing tracking.md, qa validating events), or $collect. Do NOT use from parent /sdlc, warehouse ETL, or backend APIs."
---

# Collect — tracking plans, CDC/webhooks, logs and external sources

Job: **capture the data the product needs correctly the first time.** Select only the sources the product actually needs: user behaviour events, business logs/CDC, partner webhooks/APIs, or authorized crawlers. For external-data products, verify source availability, fields and freshness before promising dependent product behavior. External collection does not require telemetry or a warehouse.

| Who loads it | Track | Deliverable | Template |
|---|---|---|---|
| `pm` (companion, `tracking: yes`) | Event requirements for this change | `01-define/tracking.md` | [templates/tracking.md](templates/tracking.md) |
| `data-collector` (`collect/tracking`) | Implementation design + proposed product tracking delta | `02-shape/collect/tracking-impl.md` · product `data/tracking-plan.yaml` | [templates/tracking-impl.md](templates/tracking-impl.md) · [templates/tracking-plan.yaml](templates/tracking-plan.yaml) |
| `data-collector` (`collect/source`) | New partner API / webhook / CDC / crawler | `02-shape/collect/data-source-analysis.md`; code only in implement | [templates/data-source-analysis.md](templates/data-source-analysis.md) |
| `data-collector` (`collect/implement`) | Implement approved event/source contracts inside scoped `source_writes` | `03-impl/collect-evidence.md`: changed files, commands, samples, limitations | — |
| `data-collector` (`collect/validate`) | Correlate known inputs through ingestion to the actual destination | `04-verify/collect-validation.md` | [templates/collect-validation.md](templates/collect-validation.md) · [tracking-validation.md](references/tracking-validation.md) |
| `qa` (companion, verify) | Event validation rows `EV-n` | rows in `04-verify/coverage.md`, referencing `collect-validation.md` | [tracking-validation.md](references/tracking-validation.md) |

## Gotchas

- **Events defined after launch cannot measure the launch, and speculative events pollute schemas.** Tracking is designed in define, implemented with the feature, validated in verify — never "补埋点" next sprint. **Decision-Bound Tracking**: every `EV-n` event in [templates/tracking.md](templates/tracking.md) must bind to a specific **decision or falsifiable hypothesis** (`H-n` / pre-committed operational rule) and feed a metric ID in `data/metrics.yaml` — strictly forbid `"先埋着以后可能用"`.
- **Names drift fastest.** Use one convention (`object_action`, past tense, `snake_case`) in `data/tracking-plan.yaml`; new events reuse existing domain objects and properties.
- **Identity & offline SDK queues require explicit boundaries.** Decide `anonymous_id` → `user_id` server-side stitching at signup/login, cross-device rules, and `anonymous_id` rotation on logout up front. Offline-capable client SDKs must bound local ring-buffer storage, record both `event_time_client` and `event_time_server` (clock-skew safe) plus monotonic `client_seq`, flush with jittered backoff, never re-stamp pre-logout queued events with the next user's identity, and purge unconsented queues on opt-out.
- **Client events lie under ad blockers, retries and offline queues.** Money, orders, entitlements and state transitions emit server-side events from committed facts; client events capture UI interaction. Never put plaintext PII in properties; consent state is gated or carried explicitly.
- **CDC & partner webhooks have strict ordering, delete and replay contracts.**
  - **CDC**: Preserve source commit ordering (`LSN` / binlog offset / `op_ts`), operation kind (`c/u/d` + tombstones for hard deletes), and watermark-aligned snapshot-to-binlog handoff with idempotent `(pk, lsn)` merge — polling `updated_at` alone silently drops hard deletes and sub-second overwrites. See [industry-data-sops.md](../schema/references/industry-data-sops.md).
  - **Webhooks**: Verify HMAC/asymmetric signature and timestamp replay window over raw bytes BEFORE parsing; persist raw payload + `delivery_id` to a durable inbox before returning fast `2xx` ACK; pair push ingestion with periodic cursor/pull reconciliation to heal sender retry blackouts.
- **Design completion is not collection completion; staging is not landed.** Distinguish `emitted → accepted → persisted → queryable` (and for crawlers, `staging → unsynced cursor → landed`). A mock-only run or HTTP `200` proves nothing about destination persistence; maintain the `unsynced` cursor atomically/recoverably across partial deletes.
- **Idempotency Key Contract & Persistent Resume.** Separate normalized `url_key`/`url_hash` (deduplication) from `content_hash` (payload change digest, [templates/item-definition.py](templates/item-definition.py)). Lock a unique constraint on `url_key`/`url_hash` (or `(job_id, url_key)` across jobs) with `ON CONFLICT DO NOTHING` / deterministic merge so at-least-once delivery converges to **effectively-once**. Crash/restart recovery must resume **strictly from persistent task, dedup, and retry tables — never from in-memory worker loop indices**.
- **UI Click ≠ Data Acquisition Success; Virtualized DOM ≠ Full Document.** When extracting from authorized rendered pages ([cdp-browser-extraction.md](references/cdp-browser-extraction.md)), read the underlying block model/cursors and actual `200` media bytes rather than viewport `innerText`, chrome, or assumed URL shapes, and stop at third-party copyrighted works. Enforce a hard exit check proving the collector distinguishes **DOM interaction success** (click/scroll/tab switch) from **underlying API/payload acquisition success** (intercepting HTTP `403`/`429`/`5xx` or business JSON errors masked by a successful click); failed requests must persist **structured `error_code`, `request_id`, and `retryable` flag** into the retry/dead-letter queue.
- **Master Data Mapping SSOT & Context Echo Reconciliation.** Entity, region, and brand mappings (`brand_id`, province/city code, category ID) must originate from a **single canonical source (SSOT)** with a reconciliation check. Before committing records or advancing checkpoints, assert that **request parameters and response payload entity/region match the active persistent checkpoint/lease** ([collection-recovery.md](references/collection-recovery.md)).
- **Crawlers are their own subsystem.** Never import the online application backend; respect ToS/rate limits and zero-item alerts; test SQL on the production dialect (`NULLS LAST` passes SQLite and crashes MySQL).
- **Classify failures, scope shared dependencies, and preserve task ownership.** Separate bad task data (dead-letter), parser/DOM drift (zero retry + alert), session/rate gates (pause within contract), and local infra faults (backoff). Stop operations sharing a failed account/session or critical quota ledger while letting independent healthy sources continue; noncritical telemetry may degrade without halting collection. Close the claim-to-pending window with atomic handoff/leases and business checkpoints ([collection-recovery.md](references/collection-recovery.md)).
- **Versioned captures, confirmed-empty, and additive checks.** Test parsers/guards in both directions against real request+response captures (injecting request-only keys like geo/date into records). Persist business-valid empty responses (`data: []`) as `confirmed-empty` rather than `missing` to prevent infinite recollect loops, and cross-sum additive hierarchies (`Σ children == parent`) before declaring pipelines healthy.

## Excellence bar

| Excellent | Reject as mediocre |
|---|---|
| Each event: `object_action` name, user-visible trigger, client/server placement, typed properties, `metrics.yaml` ID, owner, runnable validation | "加个点击埋点" |
| CDC/webhook/SDK: LSN/tombstone safety, raw-body signature + durable inbox, offline identity isolation | Polling `updated_at` without delete capture; synchronous slow webhook handler |
| External source: access contract, `url_key` vs `content_hash`, lease/checkpoint recovery, `confirmed-empty` state, real-capture regression | A spider that works once on the author's laptop |

## Steps

1. **Tracking requirements (`pm`, `01-define/tracking.md`)**: Map spec metrics to events (`EV-n`) and journeys (`J-n`) using [event-design.md](references/event-design.md) and [templates/tracking.md](templates/tracking.md), reusing `data/tracking-plan.yaml` vocabulary first.
2. **Tracking design (`data-collector`, `collect/tracking`)**: Propose delta to [templates/tracking-plan.yaml](templates/tracking-plan.yaml) (never mark unimplemented events active), specify SDK/server placement, offline queue/identity/consent rules, validation steps ([tracking-validation.md](references/tracking-validation.md)) and monitors in [templates/tracking-impl.md](templates/tracking-impl.md).
3. **External / CDC / webhook sources (`collect/source`)**: Complete [templates/data-source-analysis.md](templates/data-source-analysis.md) (type, ToS/legal, rate limits, schema, CDC/webhook/recovery boundaries). For distributed crawlers, consult [scrapy-redis-distributed.md](references/scrapy-redis-distributed.md), [anti-scraping-playbook.md](references/anti-scraping-playbook.md), and [anti-scraping-escalation.md](references/anti-scraping-escalation.md) as applicable, starting from [templates/spider-template.py](templates/spider-template.py), [templates/spider-config.py](templates/spider-config.py) and [templates/item-definition.py](templates/item-definition.py).
4. **Implement & validate (`collect/implement`, `collect/validate`)**: Implement inside `source_writes` (`03-impl/collect-evidence.md`). Trace real sample IDs end-to-end (`emitted → accepted → persisted → queryable`), verifying dedup, retries, late/offline events, `confirmed-empty`, identity and reconciliation in `04-verify/collect-validation.md` ([templates/collect-validation.md](templates/collect-validation.md)).

## Self-check

- [ ] Every `EV-n` binds to a concrete decision or falsifiable hypothesis (zero `"先埋着以后可能用"`), with `object_action` name, trigger, placement, typed properties, `metrics.yaml` ID, owner and runnable validation?
- [ ] Identity stitching, logout rotation, offline SDK queue isolation, consent and zero-PII rules enforced?
- [ ] CDC preserves LSN/tombstones & snapshot handoff; webhooks verify raw-body signatures before fast durable-inbox ACK + pull reconciliation?
- [ ] External sources lock `url_key`/`url_hash` (or `(job_id, url_key)`) unique constraints + `ON CONFLICT DO NOTHING` / deterministic merge, resume strictly from persistent task/dedup/retry tables (never worker loop indices), enforce master-data mapping SSOT + context echo reconciliation, and distinguish `confirmed-empty` from `missing`?
- [ ] Validation (`04-verify/collect-validation.md`) proves `emitted → accepted → persisted → queryable` on real samples and verifies UI click ≠ data acquisition success (persisting structured `error_code`, `request_id`, `retryable` on masked HTTP `403` / business JSON errors)?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [event-design.md](references/event-design.md) | Naming events, properties, identity stitching, client vs server, sampling, consent |
| [tracking-validation.md](references/tracking-validation.md) | Writing validation steps, `qa` verifying `EV-n`, post-launch data-quality monitors |
| [collection-recovery.md](references/collection-recovery.md) | Persistent tasks, leases, business checkpoints, shared failures, budgets or staged delivery |
| [industry-data-sops.md](../schema/references/industry-data-sops.md) | CDC log ordering, tombstones, outbox/inbox delivery, schema evolution & industry data rules |
| [scrapy-redis-distributed.md](references/scrapy-redis-distributed.md) | Building or debugging a distributed queue crawler |
| [anti-scraping-playbook.md](references/anti-scraping-playbook.md) | Assessing target site behavior within the source access contract |
| [anti-scraping-escalation.md](references/anti-scraping-escalation.md) | Diagnosing 403 / 429 / captcha / empty responses legally and safely |
| [cdp-browser-extraction.md](references/cdp-browser-extraction.md) | Extracting authorized data/media from virtualized web pages via CDP |
| [templates/collect-validation.md](templates/collect-validation.md) | End-to-end ingestion & event validation report (`04-verify/collect-validation.md`) |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
