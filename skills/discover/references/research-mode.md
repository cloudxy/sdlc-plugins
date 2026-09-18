# sdlc-research mode

AFK discovery survey. This window is the **manager**. Do not handoff. Do not write `spec.md`. Do not grill (that is `/sdlc-discover`).

the supplied arguments

Follow `PLUGIN_ROOT/skills/discover/SKILL.md` **§2 Survey** for spawn packets, native types, and the one `general-purpose` fallback. This file only adds bookkeeping the survey-only entry needs:

1. Resolve PLUGIN_ROOT (prefer `$ZCODE_PLUGIN_ROOT`). Feature dir: `.sdlc/<slug>/` or the path in the supplied arguments. Create `00-discover/` if needed. If no `state.yaml`, copy `PLUGIN_ROOT/skills/sdlc/templates/state.yaml` and set `discovery.status: pending`, `tracks.market/compete: pending`. Do **not** set `discovery.status: done` (that needs briefing freeze).
2. Execute discover §2 (researcher ∥ competitor, packet v2 with `product_context`, no SKILL.md paste), then §2b (growth, after `compete.md` exists). Record `host_spawn` on unknown type — **merge** into the existing mapping; never rewrite `host_spawn: {}`.
3. `ls` the deliverable paths. Run `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --require --hat market <feature-dir>`, `--hat compete` and `--hat growth`. Survey files must declare `泳道：Ln` (templates do).
4. Only if every required survey gate exits 0, set `discovery.tracks.market`, `.compete` and `.growth` to `done`. Leave `discovery.status: pending`. Return paths + short summary. Tell the user to run `/sdlc-discover` (discuss + falsify) or `/sdlc` after briefing freeze. Do not spawn pm.
