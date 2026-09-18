---
name: "collect"
description: "Use this skill when the spawn packet names data-collector or collect, or $collect. Do NOT use from parent /sdlc or for warehouse ETL."
when_to_use: "Spawn packet names data-collector, companion_skills includes collect (pm writing tracking.md, qa validating events), or $collect. Do NOT use from parent /sdlc, warehouse ETL, or backend APIs."
---

# Collect — tracking plans first, then logs and external sources

Job: **capture the data the product needs correctly the first time.** For an internet product that means, in order: user behaviour events (埋点), identities, server logs / CDC, and only then external sources such as partner APIs or crawlers.

| Who loads it | Track | Deliverable | Template |
|---|---|---|---|
| pm (companion, `tracking: yes`) | Event requirements for this change | `01-define/tracking.md` | [templates/tracking.md](templates/tracking.md) |
| data-collector (stage `collect`) | Implementation design + product tracking plan | `02-shape/collect/tracking-impl.md` · product `data/tracking-plan.yaml` | [templates/tracking-impl.md](templates/tracking-impl.md) · [templates/tracking-plan.yaml](templates/tracking-plan.yaml) |
| qa (verify) | Event validation rows EV-n | rows in `04-verify/coverage.md` | see [tracking-validation.md](references/tracking-validation.md) |
| data-collector (external source) | New partner API / CDC / crawler | `02-shape/collect/data-source-analysis.md` + code | [templates/data-source-analysis.md](templates/data-source-analysis.md) |

## Gotchas

- **Events defined after launch cannot measure the launch.** Tracking is designed in define, implemented with the feature, validated in verify — never "补埋点" next sprint.
- **Names drift fastest.** `click_btn_2`, `ReportView`, `report_viewed` for one action → three metrics that never agree. One convention (`object_action`, past tense, snake_case) in the product tracking plan; new events reuse existing objects and properties.
- **Identity is a design decision.** Anonymous id → user id stitching at login/signup, cross-device, and logout must be decided up front, or funnels break at registration.
- **Client events lie under ad blockers, retries and offline queues.** Money, orders and state changes are server-side events; client events are for UI behaviour.
- **PII does not belong in event properties.** No phone numbers, emails, ids of third parties in clear text; consent state is itself a property or a gate.
- **Every event serves a metric.** An event with no metric id in `data/metrics.yaml` (or a named analysis) is noise — do not add it.
- **External crawler stack (auto_agents):** Scrapy is its own subsystem (B2: never imports backend), items flow through Redis queues rather than direct DB writes, DOWNLOAD_DELAY and UA rotation are mandatory (R5/R6), zero items for 3 runs → alert. SQLite accepts PostgreSQL-only syntax such as `NULLS LAST` that MySQL rejects — test on the production dialect.

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

### Track: implementation design (data-collector, stage `collect`)

1. Merge the feature's events into the product `data/tracking-plan.yaml` (conventions, identity, common properties stay consistent).
2. Decide placement (client SDK / server / both), batching, offline behaviour, sampling, consent gating.
3. Write validation steps per event ([tracking-validation.md](references/tracking-validation.md)) and post-launch data-quality monitors.
4. Write `02-shape/collect/tracking-impl.md`; record the product-layer delta.

### Track: external sources

1. Analyse the source with [templates/data-source-analysis.md](templates/data-source-analysis.md): type (API / HTML / RSS / CDC), scope, rate limits, ToS and legal review, freshness need, schema.
2. Partner APIs and CDC: retries with backoff, idempotent ingestion keys, schema validation at ingestion, lag monitoring.
3. Crawlers: follow [scrapy-redis-distributed.md](references/scrapy-redis-distributed.md) and [anti-scraping-playbook.md](references/anti-scraping-playbook.md); when blocked, diagnose with [anti-scraping-escalation.md](references/anti-scraping-escalation.md) and escalate countermeasures in cost order. Start from [templates/spider-template.py](templates/spider-template.py), [templates/spider-config.py](templates/spider-config.py) and [templates/item-definition.py](templates/item-definition.py).

## Self-check

- [ ] Every event has name, trigger, placement, typed properties, metric id and owner?
- [ ] Names and properties reuse the product tracking plan conventions?
- [ ] Identity stitching, consent and PII rules referenced, not reinvented?
- [ ] Validation steps exist for every EV-n, and qa's matrix can reference them?
- [ ] Product `data/tracking-plan.yaml` updated and the delta recorded?
- [ ] External sources: rate limit, ToS/legal, retries, schema checks, zero-data alert?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [event-design.md](references/event-design.md) | Naming events, properties, identity, client vs server, sampling, consent |
| [tracking-validation.md](references/tracking-validation.md) | Writing validation steps, qa verifying EV-n, post-launch data-quality monitors |
| [scrapy-redis-distributed.md](references/scrapy-redis-distributed.md) | Building or debugging a distributed crawler |
| [anti-scraping-playbook.md](references/anti-scraping-playbook.md) | Assessing a new target site, designing countermeasures |
| [anti-scraping-escalation.md](references/anti-scraping-escalation.md) | 403 / 429 / captcha / empty responses |
| [templates/tracking-plan.yaml](templates/tracking-plan.yaml) | Bootstrapping or extending the product tracking plan |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
