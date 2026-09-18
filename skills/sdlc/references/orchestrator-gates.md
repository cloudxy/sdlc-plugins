# Orchestrator gates — host facts, spawn fallback, G-fresh, acceptance, rework

Read this when a spawn fails, when resuming a feature, after a G-fresh or acceptance failure, or when rework reaches 3. Do not paste this file into spawn prompts.

The `/sdlc` window is the **manager** (agents-as-tools). Spawns are nested specialist calls. Do not handoff the conversation to a hat. Persist findings and run `check-sdlc.sh` yourself.

## 0. Host facts (read on demand)

Full list for maintainers: `PLUGIN_ROOT/adapters/HOST-NOTES.md`. What the manager must know:

- **ZCode executes plugin agents as `pluginName:bareName`** — always spawn `sdlc-workflow:<role>`.
- **Agent body is who; skills are how.** Hats load `sdlc-workflow:<proc>` with the Skill tool; pass PLUGIN_ROOT so a hat can Read `skills/<proc>/SKILL.md` if Skill fails. Agent frontmatter never carries `skills:` (a non-empty list is an allowlist that blocks companion skills and the reviewer pool).
- **Research, product, design and architecture hats have `WebSearch` / `WebFetch`**; UI evidence is Bash + `scripts/ui-evidence.sh` (Playwright). Optional MCP tools come only from `adapters/extra-tools.json`, rendered at compile time.
- **Default `check-sdlc.sh` skip is exit 0.** After a producing hat, run with `--require` / `--hat`. Confirm files exist first — agent said so ≠ file exists.
- **If role work happens in the manager window, G-fresh is fake.** Iron rule 4.
- **Agent definitions are a session-start snapshot.** After re-rendering agents, smoke-test in a new window.
- **bash 3.2:** `$HAT（` is one identifier — use `${HAT}` before full-width punctuation.

## 1. Spawn recipe

The first spawn is always `subagent_type: "sdlc-workflow:<role>"` with a SPAWN PACKET v2 (task + paths + PLUGIN_ROOT + product context). Never paste SKILL.md.

If the host returns **unknown / unregistered type**, spawn **once** as `general-purpose` with the same packet. Its first action is to Read:

- `PLUGIN_ROOT/agents/<role>.md`
- `PLUGIN_ROOT/skills/<proc>/SKILL.md` (resolve the task’s primary skill from [stage-map.md](stage-map.md))

Record in `state.yaml` (merge under the role key; never write an empty `host_spawn: {}`):

```yaml
host_spawn:
  <role>:
    requested: "sdlc-workflow:<role>"
    available: [<types the host listed>]
    fallback: general-purpose
    reason: "host has no pluginName:bareName table"
```

**Dual dispatch** = native and general-purpose both succeed for the same hat. One unknown-type retry is not dual dispatch. Do not start with general-purpose when native types exist.

## 2. G-fresh fail does not advance the hat

After define / shape / implement (L1+), and at the final review:

1. Write `05-review/findings.md` from the reviewer's **final message** before any other spawn. If an earlier `findings.md` has a different `## Snapshot`, copy it to `findings-<stage>.md` first.
2. blocker > 0 or major > 0 (unwaived): `current_hat` stays on the producing stage; `hats_done` does not gain it.
3. Spawn the producer to fix, then a **new** reviewer on the new files (a new snapshot is not reviewer shopping).
4. `review_findings[].status: fixed` is bookkeeping written only after a later G-fresh verified that id independently.

`check-sdlc.sh --require` fails **HATADVANCE** when `current_hat` ranks past the stage of the last failed fresh-context gate (ranks in [stage-map.md](stage-map.md)).

## 2b. Acceptance fail (v4)

Acceptance is not a fresh-context gate — it is a verdict by pm, designer and growth on the running build.

1. Any `accept-*.md` with `结论：不通过` fails `check-sdlc.sh` (ACCEPT) for the whole tree until a new acceptance run replaces it.
2. Merge the gap lists from all acceptance files into one rework packet per implement hat (UI gaps → frontend, API/data gaps → backend). `current_hat: implement`, `rework_rounds` +1; from round 2 attach `debug_protocol`.
3. After the fix: re-run the implement G-fresh only if contracts or schemas changed; always re-run verify (E2E) and every acceptance hat whose verdict was not `通过`.
4. A gap that is really a spec or design problem (the build matches the spec, the spec is wrong) goes back to define or designer — record it in `lane_changes` or `stale_artifacts`, do not bend the implementation.
5. `有条件通过` → present the conditions to the user; accepted conditions go into `open_questions` with an owner; otherwise treat as `不通过`.

## 3. Rework ≥ 3 on the same hat

Three G-fresh fails (or acceptance rounds) on the same stage → **stop**, report "systemic", wait for the operator. From round 2 on, respawns attach `debug_protocol` ([debug-loop.md](debug-loop.md)) and the gate records a one-line `root_cause`.

## 3b. Resume derivation (write back when `phase` is missing)

Normalize legacy Chinese `current_hat` / `hats_done` to English first (once). Then derive `phase`:

| `current_hat` on disk | last fresh-context / acceptance | derived `phase` |
|---|---|---|
| missing and lane = L0 | — | L0done |
| empty/`define` and `discovery.status: pending` | — | Discovering |
| `define` and no fresh gate | — | HatReady |
| any, last fresh = `fail` or any accept `不通过` | fail | Rework |
| any, last fresh = `pass`, lane unfinished | pass | HatReady |
| `hats_done` covers `required_hats_done(lane)` | pass | Closed |
| unparseable | — | HatReady (conservative) + note in open_questions |

`required_hats_done(lane)` is in [stage-map.md](stage-map.md); v4 features include `accept`, legacy features do not. `check-sdlc.sh` does not read `phase`.

## 4. Expected paths

After each spawn, `ls` the deliverable paths from the packet. Missing path = hat not done. An empty `tickets/` with the table only in `contract.md` is allowed only if the packet said Wave 1 stays in the table.

## 5. Skill pitfalls files

Write `skills/<proc>/references/*-pitfalls.md` only for items with **code + test, an escape id, or a gate command + exit code**. Speculation stays in diagnosis notes.

## 6. User-named all-roles diagnosis

If the operator lists many roles, that is a **diagnostic fan-out**, not "L4 by default". Skip roles with no surface via `roles_skipped` + why. qc during define is a coverage-gap diagnosis, not a release opinion.

## 7. Shape split

If the frozen FR count > 20, the first architect spawn writes `contract.md` + ADRs + the ticket **table**; a second spawn writes `tickets/T-nn.md`.

## 8. Design direction pick (v4, `ui: yes`)

1. After designer `explore`, check `02-shape/design-directions.md` lists ≥3 directions (D1…Dn), each with screenshots under `02-shape/prototypes/`.
2. Present one line per direction (signature moment · main trade-off · screenshot paths) and the designer's recommendation. Wait for the human.
3. Record `design.picked`, `design.picked_by` (`user` or `delegated`), `design.at`. Spawn designer `specify` with the pick in the packet `task` line; the designer writes `选定：D<n>` into `design-directions.md`.
4. The user rejects all directions → respawn `explore` with their feedback as an input file (`02-shape/direction-feedback.md`); this counts as design rework, not a new lane.

## 9. Discovery survey scale

If `00-discover/market.md` already has an E3 counted snapshot (number + source + window), do **not** spawn a second researcher round. competitor still writes 现状; growth still writes positioning hypotheses. Survey hats become 1–2, not 3.

## 10. Product layer failures

| Gate tag | Meaning | Manager action |
|---|---|---|
| PRODUCTCTX | a product file the stage needs is missing or still carries `sdlc:unfilled` | respawn the owner hat with that file in `product_writes`, or run `/sdlc-product` |
| WRITEBACK | `product-delta.md` missing at the final review, or it names a product file that does not exist | write the delta rows the hats returned (you own `product-delta.md` and `CHANGELOG.md`); a row naming a missing file → respawn that owner; nothing changed → `无产品层变更：<理由>` |
| unowned edit | a hat changed a product file it does not own (seen in the delta) | reviewer raises a major; route the change to the owner |
| DECISIONPENDING | a strategic `Q-*` row is still 待确认 while the feature tries to leave define/shape, or at the product gate | **not rework.** Present the pending rows (options + recommendation) to the operator in one round and wait. After an explicit answer, respawn the owner to write 已确认 + the operator's words. No answer → `phase: Stopped`, reason `waiting-for-operator` |
| DEFAULTED | a strategic row marked 默认, 已确认 without the operator's words, or 默认已定 / "未应答…按推荐" text | rework on the producer: turn it back into 待确认 with options, remove the settled wording from dependent sections, then ask the operator |
| PRODUCTUI | `design-system.md` cites no screenshot that exists | the designer described screens nobody looked at: start the app (§12), respawn the designer to capture the existing UI with `scripts/ui-evidence.sh` and cite the PNGs |

## 11. `host_spawn` merge

Record fallbacks under `host_spawn.<role>`. Never replace a non-empty mapping with `host_spawn: {}` (YAML keeps the last duplicate key). `check-sdlc.sh` flags two `^host_spawn:` keys as HOSTSPAWN.

## 12. The app must run (v4)

Screenshots, integration runs, E2E, design QA and acceptance walkthroughs all need the running product. Reading source code is not a substitute (2026-09-17: a whole run finished without once starting a project that has two frontends).

1. **Step 0 / `/sdlc-product` step 1:** `python3 <PLUGIN_ROOT>/scripts/check_config.py --project-root <root>`. Blockers (APP-START, APP-URL, E2E, NO-CONFIG) → show the findings and the suggested block to the user and ask them to update `sdlc.config.yaml`. You never write the user's config.
2. **Before a stage that needs the app** — designer explore/design QA on an existing product, `/sdlc-product` designer, implement integration, verify E2E, accept: `check_config.py --project-root <root> --probe`. It probes `app.base_url` and every `app.urls` entry (products with several UIs or an API health URL); put the URLs the stage needs into the packet.
3. **APP-DOWN** → run `app.start` in the background (keep its output in `.sdlc/<feature>/app-start.log`), wait, probe again — at most three probes over about a minute.
4. **Still down** → stop (`phase: Stopped`, reason `app-not-running`) and tell the user the command, the URL and the last log lines. Do not continue on screenshots of prototypes, curl output or code reading in place of the product.
