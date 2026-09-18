# Product layer — the product's memory across features (v4)

Read this at Step 0, when filling `product_context` / `product_writes` in any packet, when running `/sdlc-product`, or after a `PRODUCTCTX` / `WRITEBACK` gate failure.

**Why it exists.** Up to v3 every feature was designed from zero: pm never saw the product's core value path, the DBA never saw a domain model, the designer never saw a design system, growth had nowhere to keep positioning. Core-feature judgement, extensible schemas, coherent design and precise marketing are all *product-level* properties — they cannot emerge from a pipeline that only ever sees one feature. The product layer is the durable context every hat reads first and every producing hat keeps true.

## Location

`product_root` in `sdlc.config.yaml` (default `docs/product`, relative to the project root). Copy it into each new feature's `state.yaml` as `product_root:` together with `sdlc_version: 4`.

## Files and templates

Write ownership is generated in [stage-map.md](stage-map.md#product-write-ownership) from `workflow/registry.json`. Product packets may narrow that scope. PM contributes event proposals through tracking.md; the collector owns tracking-plan.yaml. Analyst updates only hypothesis status in strategy.md; PM owns strategy decisions.

| File under `product_root` | Template | Main readers |
|---|---|---|
| `strategy.md` | `skills/prd-gwt/templates/product-strategy.md` | everyone |
| `feature-map.md` | `skills/prd-gwt/templates/feature-map.md` | everyone |
| `growth.md` | `skills/growth/templates/growth-playbook.md` | pm, designer, ops, analyst |
| `design-system.md` | `skills/design-contract/templates/design-system.md` | frontend, qa, growth, pm |
| `architecture.md` | `skills/architecture/templates/architecture-baseline.md` | dba, backend, frontend, sre, qa |
| `domain-model.md` | `skills/schema/templates/domain-model.md` | architect, backend, data hats |
| `erd.dbml` | `skills/schema/templates/erd.dbml` | architect, backend, data hats |
| `data/tracking-plan.yaml` | `skills/collect/templates/tracking-plan.yaml` | pm, frontend, backend, qa, analyst |
| `data/metrics.yaml` | `skills/warehouse/templates/metrics.yaml` | pm, growth, analyst, sre |
| `data/tags.yaml` | `skills/warehouse/templates/tags.yaml` | growth, miner, analyst |
| `CHANGELOG.md` | `skills/sdlc/templates/product-changelog.md` | reviewer, humans |
| `README.md` | `skills/sdlc/templates/product-readme.md` | humans |

## The unfilled marker

Every template carries the token `sdlc:unfilled` (an HTML comment in markdown, a `#` comment in YAML, a `//` comment in DBML). The owner deletes the marker only when the file holds real content for *this* product. Gates treat a file whose marker comment is still present (a line starting with `<!--`, `#` or `//` followed by the token) as missing; prose that merely mentions the token does not count.

## Bootstrap

1. The manager creates `product_root` and copies templates for files that do not exist yet (never overwrite).
2. There is no separate bootstrap lane. The first hat that needs a file fills it from evidence — pm fills `strategy.md` + `feature-map.md` at define, the designer fills `design-system.md` at explore, the architect fills `architecture.md` at shape, and so on.
3. For an existing product, run `/sdlc-product` first: it fills the whole layer up front, so the first feature starts with real context.
4. Reverse engineering counts as evidence: architecture from code and deploy files, the domain model from migrations and ORM models, the design system from existing tokens and screenshots, the tracking plan from existing tracking calls, metrics from dashboards. Mark inferences `[推断]` and list them as open questions for the owner.

## Per-hat packet defaults

Paths are relative to `product_root`; the manager expands them to absolute paths in the packet. The lists are deliberately short: every file in `product_context` is read in full by every spawn of that hat, so each extra file multiplies across a run. Add a file only when the task needs it, and say why in the packet.

| Hat (task) | `product_context` (read first) |
|---|---|
| researcher · competitor | strategy.md |
| growth (positioning) | strategy.md, growth.md |
| pm (define) | strategy.md, feature-map.md; + data/metrics.yaml when the spec moves a metric; + data/tracking-plan.yaml when `tracking: yes` |
| designer (explore) | strategy.md, design-system.md; + growth.md when it names a highlight on this journey |
| designer (specify) | design-system.md |
| architect | architecture.md, domain-model.md; + strategy.md when scale assumptions drive the scenarios |
| dba | feature-map.md (roadmap stress test), domain-model.md, erd.dbml |
| data-collector | data/tracking-plan.yaml, data/metrics.yaml |
| data-warehouse-engineer | data/tracking-plan.yaml, data/metrics.yaml, data/tags.yaml |
| frontend | design-system.md, architecture.md |
| backend · algo · miner | architecture.md, domain-model.md; + data/tracking-plan.yaml when `tracking: yes` |
| qa | data/tracking-plan.yaml when `tracking: yes` (journeys come from the spec) |
| pm (accept) | feature-map.md |
| designer (accept) | design-system.md |
| growth (accept · launch) | growth.md, data/metrics.yaml; + data/tags.yaml at launch |
| ops | strategy.md, growth.md |
| sre | architecture.md |
| analyst | strategy.md, data/metrics.yaml |
| reviewer · qc | every product file listed in `<feature>/product-delta.md` (read-only) |

## Packet inputs — files, not trees

`inputs` lists files the hat must read. Directories belong in `explore_roots`: the hat searches them with Grep/Glob and opens only what it needs. A 2026-09-17 bootstrap listed `docs/`, `.sdlc/` (443 files), `backend/app/api` and both frontends' `pages/` as inputs, and the run consumed about 38.7M input tokens. `scripts/check_packet.py` rejects directory inputs and oversized `product_context`.

## Size budgets

Product files are read first by many spawns, so they stay short: durable facts, not feature detail. `check-sdlc.sh --hat product` warns (PRODUCTSIZE) above the budget and fails above twice the budget.

| File | Lines |
|---|---|
| strategy.md | 120 |
| feature-map.md | 200 |
| growth.md | 200 |
| design-system.md | 250 |
| architecture.md | 250 |
| domain-model.md | 300 |
| README.md | 60 |

YAML and DBML files have no line budget; only their owners and the data hats read them in full.

## References between files

Markdown product files name data definitions instead of restating them: `metric:<id>` (an `id` in `data/metrics.yaml`), `tag:<id>` (an `id` in `data/tags.yaml`), `event:<name>` (an `event` in `data/tracking-plan.yaml`). Gate REFS fails when a reference has no definition — the two-truths drift starts exactly there. The check runs only once the data file is filled.

## Stale files

Upstream changes make downstream files stale: `strategy.md` → `growth.md`, `design-system.md`, `architecture.md`, `data/metrics.yaml`; `feature-map.md` → `growth.md`, `design-system.md`, `domain-model.md`, `data/tracking-plan.yaml`; `architecture.md` → `domain-model.md`; `domain-model.md` → `data/tracking-plan.yaml`; `data/tracking-plan.yaml` → `data/metrics.yaml`; `data/metrics.yaml` → `data/tags.yaml`, `growth.md`; `data/tags.yaml` → `growth.md`. `check-sdlc.sh --hat product` reads `CHANGELOG.md` in order and warns STALE when an upstream file changed after its downstream file was last written. Respawn the downstream owner, or record why the change does not affect it.

## Writeback protocol

- Owners edit their product files **in place** — the files describe the product as it is now, they are not append-only logs.
- Hats **return** one row per change (`file | section | change | reason`); the manager writes it to `<feature>/product-delta.md` (template `skills/sdlc/templates/product-delta.md`) and `product_root/CHANGELOG.md`. Hats never edit those two files: parallel hats appending to one file lose rows.
- A hat that needs a change in a file it does not own (e.g. the designer needs a new domain concept) raises an open question to that owner instead of editing the file.
- No change to the product layer → `product-delta.md` holds the line `无产品层变更：<理由>`.
- v4 gate: `--hat review` requires `product-delta.md`, and every product file it names must exist. The reviewer checks that the product files and the feature artifacts agree.

## Decisions — who decides what

Product-level decisions live in `strategy.md` §9, feature-level ones in the spec's open-question table, one `Q-*` row each with a category and a status.

| Category | Examples | Who decides | Row before the answer | Row after |
|---|---|---|---|---|
| 战略 (strategic) | who to serve first, positioning, core value and Aha, pricing and paywalls, launch or gate timing, north star, scope cuts, money / data loss / security / compliance, anything hard to reverse | the operator, explicitly | 待确认 + options + the hat's recommendation; dependent text says 「待 Q-… 决定」 | 已确认 + 「the operator's words」 · who · date |
| 运营 (operational) | a reversible detail inside decided strategy: page size, default sort, a threshold with a revisit trigger | the owning hat | — | 默认 + reason (listed in the manager's report) |

- **Silence is not consent.** A question the operator did not answer stays 待确认, and the work that depends on it waits. "按推荐" said by the operator is an answer. A question tool returning nothing is not.
- **Gates.** DEFAULTED: a strategic row marked 默认, 已确认 without the operator's words, or 默认已定 / "未应答…按推荐" in product or feature text (CHANGELOG is history and is not scanned). DECISIONPENDING: a strategic row still 待确认 at the product gate or when a feature leaves define/shape.
- 2026-09-17: `/sdlc-product` adopted five unanswered strategic calls (market opening, first paywall, checkout trigger, AI planning entry, the Aha gold standard) as 「默认已定·待复核」 and spread them through strategy, feature-map, growth and README. This section exists so that cannot pass a gate again.

## Anti-patterns

| Anti-pattern | Why it hurts | Instead |
|---|---|---|
| Copying feature specs into the product layer | The layer grows unreadable; nobody reads it first | Only durable facts: value path, journeys, domain concepts, principles, scenarios, event and metric ids |
| `strategy.md` longer than two screens | Hats skim it and miss the core value | Put detail in `feature-map.md` / `growth.md` |
| Feature shipped, map still says "Next" | The DBA's roadmap stress test uses stale plans | pm accept updates `feature-map.md` status |
| Silent re-definition (a metric, a term, a token) in a feature file | Two truths; drift starts here | Change the product file and record it in the delta |
