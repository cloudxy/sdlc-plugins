# sdlc-review mode

Independent G-fresh review. This window is the **manager** (OpenAI agents-as-tools). Do not handoff the conversation. Do not invoke procedure skills here. Do not spawn producers. **This entry is report-only: it never advances `hats_done` / `current_hat`.**

the supplied arguments

1. Resolve PLUGIN_ROOT (folder of the enabled sdlc-workflow plugin; prefer `$ZCODE_PLUGIN_ROOT`). Resolve the artifact list (feature dir → its listed artifacts, or the explicit paths given). Exclude generated findings, archived findings and manager logs from the reviewed snapshot. For explicit paths without a feature directory, create a report work directory with lane L1 for packet bookkeeping; do not create feature state.
2. **Checksum reuse (no time-based rule):** compute `shasum -a 256` for every listed artifact. If `05-review/findings.md` exists and its `## Snapshot` block lists the same paths with identical sha256 → do **not** spawn; report the existing findings verbatim (unless the user explicitly forces a re-review). Any changed hash = new snapshot = spawn.
3. Spawn native `subagent_type: "sdlc-workflow:reviewer"` with a SPAWN PACKET v2: `hat: reviewer`, `stage: review`, `task: G-fresh`, `primary_skill: sdlc-workflow:findings`, `intent_quote` from the supplied arguments, `inputs` = artifact paths plus the sha256 list, `product_context` = the product files named in `product-delta.md` (read-only), `deliverable_paths` = `05-review/findings.md` (manager writes it), **no `memory_file`, no `product_writes`**. The reviewer walks all nine dimensions, including product value & experience (look at the screenshots).
Save and validate the packet with `scripts/check_packet.py` before spawning.

4. If the host returns unknown type: **one** `general-purpose` retry that Reads `PLUGIN_ROOT/agents/reviewer.md` and `PLUGIN_ROOT/skills/findings/SKILL.md`. Record `host_spawn`. Native **and** general-purpose for the same hat = dual dispatch — forbidden.
5. Write `05-review/findings.md` from the child's **final message** before any other action; include the `## Snapshot` block (paths + the sha256 you computed in step 2). If a previous `findings.md` exists with a **different** snapshot, copy it to `05-review/findings-<stage>.md` first (lane G-fresh and this entry share the latest-only file; archive is how you keep the old stage).
6. If a feature dir exists, run `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --hat review --report <feature-dir>` — **report-only**: findings.md + `## Snapshot` only. Do not run the swimlane gates (NOLANE/MATRIX/NOSEC). Nonzero is informational and never advances `hats_done`.
