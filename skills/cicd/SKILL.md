---
name: cicd
description: "Use this skill when the spawn packet asks to wire gates into CI or $cicd. Do NOT use from parent /sdlc or for incidents."
when_to_use: "Spawn packet asks to export gates into CI, or $cicd. Do NOT use from parent /sdlc, release checklists, or incidents."
---

# CI wiring — run the same gates per push, not only per hat

Procedure for exporting the project's **existing** gates into CI. CI here is another runner of G-script, **not a new gate kind**: the commands and their exit semantics are exactly what `sdlc.config.yaml` and `check-sdlc.sh` already define. The plugin owns no CI platform (slice, A) — this skill writes the project-side wiring only.

Purpose: a violation caught at push time costs one commit; the same violation discovered at the next hat's `--require` costs a context switch and often a rework round. CI is the cheapest place to intercept.

## The wiring

1. **Inventory the gates.** From `sdlc.config.yaml`: test/lint/build/migration commands. From the plugin: `bash <PLUGIN_ROOT>/scripts/check-sdlc.sh --require --hat <stage> <feature-dir>` per producing stage the project actually uses.
2. **Map to pipeline steps.** One CI step per gate, `fail-fast` on the cheapest first (lint → test → build → migration → check-sdlc). Do not wrap exits: the step's exit code **is** the gate result — translating a nonzero into a warning is gate laundering.
3. **Feature-dir discovery.** If the repo keeps `.sdlc/<feature>/` trees, select changed/active features and their declared completed stages and delivery goals. Do not fail an unrelated archived or intentionally plan-only feature for never reaching a later stage.
4. **Fingerprints as artifacts.** Upload the gate command + exit code log as a CI artifact; that log is admissible as `gates[]` script evidence (same format the hat would paste) — reuse only when commit/tree, dirty state, dependencies, configuration, gate version, environment and relevant external inputs match; a commit SHA alone is insufficient.
5. **Secrets.** CI credentials live in the CI secret store, never in `sdlc.config.yaml`, never in the step script. A gate that needs a secret names it by reference.
6. **Document the mapping** in the project README: gate → CI step → artifact name, so a red CI run is traceable to the same command the orchestrator runs.

## Gotchas

- **CI green ≠ review pass.** CI is G-script only; G-fresh stays a reviewer spawn. Automated model review may supplement deterministic checks, but cannot impersonate the independent reviewer or silently replace required evidence.
- **Do not fork gate definitions.** If CI needs a different command than `sdlc.config.yaml`, the config is wrong — fix the config, then CI inherits it. Two sources of gate truth = the config silently rots.
- **Main-branch discipline.** Feature branches may be mid-lane red on `--hat <future-stage>`; scope per-stage requires to the stages already done on that branch, on main require only the stages promised by the affected feature's accepted delivery goal.
- **No new gate kinds.** Coverage thresholds, security scanners etc. enter as `sdlc.config.yaml` commands first; CI just runs them.

## Self-check

- [ ] Every CI step maps 1:1 to a config/plugin command (no invented gates)?
- [ ] Exit codes passed through untranslated?
- [ ] Gate logs uploaded as artifacts in `gates[]`-admissible form?
- [ ] Secrets only by reference?
- [ ] Branch scoping: `--hat` per done stages on feature branches, goal-appropriate completed-stage checks on main?

## Registered task

`sre/deliver/ci` writes `06-deliver/ci.md` with the gate-to-pipeline mapping, changed project CI files, runner/toolchain pinning, a real run URL/log (or an explicit unexecuted limitation), and evidence reuse conditions. It is a partial task and may run during implementation; it cannot imply deployment. Project `source_writes` authorizes scoped pipeline/config edits. Keep gate commands in the existing project command/config source and reference them from CI; do not copy a second authoritative command list into prose. CI changes should be validated by syntax/config checks and an appropriate representative run where available.
