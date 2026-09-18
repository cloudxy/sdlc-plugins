# sdlc-product mode

Product-layer build. This window is the **manager**: do not handoff, do not write product files yourself (Iron rule 4), do not invoke procedure skills here. You are the only writer of `CHANGELOG.md`, `README.md` and `.sdlc/_product/*`. Every hat reads the product layer before feature work — this command makes it real instead of templates.

the supplied arguments

1. **Resolve** PLUGIN_ROOT (prefer `$ZCODE_PLUGIN_ROOT`), the project root (folder with `sdlc.config.yaml`; copy the template if missing) and `product_root` (default `docs/product`). Read `PLUGIN_ROOT/skills/sdlc/references/product-layer.md`.
2. **Preflight** (nothing spawned yet):
   - `python3 <PLUGIN_ROOT>/scripts/check_config.py --project-root <root>`. Show blockers and the suggested block to the user; they edit `sdlc.config.yaml`, you never do. APP-START / APP-URL unresolved → the designer step cannot run (step 4.4); say so now, not at the end.
   - Scaffold missing files from the templates (never overwrite), plus `README.md` and `CHANGELOG.md`. Work dir `.sdlc/_product/`: `progress.md` (one line per step) and `packets/`.
3. **Scope** from the supplied arguments (default: everything still carrying `sdlc:unfilled`). Skip surfaces the product does not have (no UI → no `design-system.md`; no data line → no `data/*`) and write the reason into `README.md`.
4. **Spawn in this order.** One hat per step; `∥` only where the hats write disjoint files and read none of each other's output. Each spawn: SPAWN PACKET v2 with `stage: product`, `task`, `product_writes` = the files that hat owns, `product_context` = upstream files already filled, `inputs` = named files only (entry points: README, CONTEXT, route tables, migrations index, analytics exports), `explore_roots` = directories it may search with Grep/Glob but not read wholesale. Save it to `.sdlc/_product/packets/<n>-<role>.md` and run `python3 <PLUGIN_ROOT>/scripts/check_packet.py <that file>` before spawning; fix every error. Its `success_checks` carries the contract's `success_check` (`python3 <PLUGIN_ROOT>/scripts/workflow.py contract --role <role> --stage product --task <task>`); for product tasks both `--root` and `--product-root` are the product_root, because product files live there, not under `.sdlc/_product/`. After each return, append the hat's delta rows to `CHANGELOG.md` and a line to `progress.md`.
   1. **pm** (`task: bootstrap`) → `strategy.md`, `feature-map.md` from evidence: docs, existing features in code, user-facing copy, analytics. Strategic questions come back as `Q-*` rows (类别 战略, 状态 待确认) in `strategy.md` §9 with options and a recommendation.
   2. **Operator decisions — wait.** Ask every strategic `Q-*` in one round: question, options, pm's recommendation. Only an explicit answer counts: silence, a question tool that returns nothing, or a question the user never saw is not consent. "按推荐" said by the user is an answer. **No answer → stop here** and report what is waiting (the rest depends on positioning, the core value path and the business model; nothing continues on assumed answers). Record answers verbatim in `progress.md`.
   3. **pm** (`task: apply-decisions`, input `progress.md`) → writes 已确认 + the user's words into §9 and updates the text that depended on them.
   4. **architect** (code, deploy files → `architecture.md`) ∥ **designer** (→ `design-system.md`). The designer needs the running product: `check_config.py --project-root <root> --probe`; APP-DOWN → start it per `skills/sdlc/references/orchestrator-gates.md` §12. It captures every UI surface in `app.urls` (else `app.base_url`) with `scripts/ui-evidence.sh` into `.sdlc/_product/screens/` and cites the PNGs (gate PRODUCTUI). The app cannot run → skip the designer, record why in `progress.md` and the report. Never let it reconstruct the UI from source code.
   5. **dba** (after architect) → `domain-model.md`, `erd.dbml` (migrations, ORM models, live schema if readable).
   6. **data-collector** (after dba — event objects use domain terms) → `data/tracking-plan.yaml`. Only if the product has a data line.
   7. **data-warehouse-engineer** (after data-collector — metrics are computed from events) → `data/metrics.yaml`, `data/tags.yaml`.
   8. **growth** (last — highlights sit on feature-map journeys, segments reference `tag:<id>`, KPIs reference `metric:<id>`; web research required) → `growth.md`.
   On an unknown type: one `general-purpose` fallback that Reads `PLUGIN_ROOT/agents/<role>.md` and the owning skill; note it in `progress.md`.
5. **Gate:** `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --hat product <product_root>`.
   - PRODUCTCTX → respawn the owner with the failing line.
   - DECISIONPENDING → back to step 4.2 (ask); not rework.
   - DEFAULTED → pm rework: back to 待确认 with options, then ask.
   - PRODUCTUI → designer with the running app.
   - SOURCES → the owner redoes its web research.
   - REFS (a `metric:` / `tag:` / `event:` reference with no definition) → respawn the owner of the referencing file once.
   - STALE and PRODUCTSIZE warnings → respawn the owner of the stale or oversized file once, or record why not in `progress.md`.
6. **Independent review:** use `stage: product`, `task: G-fresh`, `primary_skill: sdlc-workflow:findings`, product_root and a packet with no memory/product_writes; save and validate it with `check_packet.py`, then spawn `sdlc-workflow:reviewer` (no memory, no Write) on all product files. Focus:
   - consistency across files: the north star in `strategy.md` exists in `data/metrics.yaml`; every highlight in `growth.md` maps to a journey in `feature-map.md`; domain terms match tracking event objects; `architecture.md` scenarios match `strategy.md` scale assumptions;
   - inferences marked `[推断]`;
   - strategic calls written as settled without the user's words;
   - each file judged against its owning skill's excellence bar.

   Write the findings to `.sdlc/_product/findings.md` and route blocker/major findings to the owners once.
7. **Report** to the user:
   - files filled, and surfaces skipped with the reason;
   - the user's decisions, quoted;
   - operational defaults the hats applied (the user can overturn any);
   - key facts: positioning, core value path, north star, architecture stage, domain contexts;
   - anything still waiting on the user;
   - the recommended first feature to run through `/sdlc`.
