# Data Collector Excellence & Review Rubric

Apply alongside [collect SKILL.md](../SKILL.md) across `01-define/tracking.md`, `02-shape/collect/*`, `data/tracking-plan.yaml`, `03-impl/collect-evidence.md` and `04-verify/collect-validation.md`.

## 1. Stage & Track Calibration

| Track | Excellence Bar | Reject (`major` / `blocker`) |
|---|---|---|
| `tracking` (`01-define/tracking.md` · `tracking-impl.md`) | Metric-derived `EV-n` anchored to `J-n` and `metrics.yaml`; `object_action` past-tense `snake_case`; server truth for money/orders; runnable `qa` checks | Button-named events (`click_btn`), duplicate events per behavior, unimplemented events marked `active`, or plaintext PII |
| `source` (`data-source-analysis.md`) | Explicit ToS/access contract, rate budget, schema, CDC/webhook ordering & replay boundaries, failure classification and recovery checkpoints | Bypassing CAPTCHAs/paywalls, unauthorized proxy/UA rotation pools, or copying third-party copyrighted works |
| `implement` & `validate` (`collect-validation.md`) | Scoped `source_writes`; real sample IDs traced across `emitted → accepted → persisted → queryable` with dedup and count/sum reconciliation | Claiming collection complete from design docs, mock runs, or client HTTP `200` alone |

## 2. Offline SDK, CDC & Webhook Engineering

- **Identity stitching & offline SDK isolation**: Signup/login links `anonymous_id` to `user_id` server-side; logout rotates `anonymous_id`. Offline-capable client SDKs bound ring-buffer size, record both `event_time_client` and `event_time_server` plus `client_seq`, never re-stamp pre-logout queued events with the next user's identity, and purge unconsented queues on opt-out.
- **CDC completeness**: Preserve source commit ordering (`LSN` / binlog offset / `op_ts`), hard-delete tombstones, and watermark-aligned snapshot-to-log handoff with idempotent `(pk, lsn)` merge — never rely on `updated_at` polling alone when deletes or sub-second updates exist.
- **Webhook durability**: Verify cryptographic signature and replay window over raw request bytes BEFORE parsing; persist raw payload + `delivery_id` to a durable inbox before returning fast `2xx` ACK; pair push with periodic cursor reconciliation.

## 3. External Crawler Hygiene & Recovery Boundaries

- **Identity vs payload hashing**: Separate normalized `url_key` (URL deduplication) from `content_hash` (normalized business payload digest for change detection), validating item types/ranges at source before queue handoff.
- **Ownership, blast radius & `confirmed-empty`**: Close claim-to-pending gaps via atomic leases + commit token checks; bind checkpoints to business keys (never viewport pixels); halt tasks sharing a failed account/quota ledger while independent healthy sources continue; persist valid `data: []` as `confirmed-empty` distinct from `missing`/timeout.
