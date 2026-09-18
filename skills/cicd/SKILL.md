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
3. **Feature-dir discovery.** If the repo keeps `.sdlc/<feature>/` trees, run check-sdlc per feature dir (a small loop in the step script); an unfinished feature failing `--require` mid-lane is expected **only** on its own branch — main must be green (see Gotchas).
4. **Fingerprints as artifacts.** Upload the gate command + exit code log as a CI artifact; that log is admissible as `gates[]` script evidence (same format the hat would paste) — no re-run needed at hat time for the same commit sha.
5. **Secrets.** CI credentials live in the CI secret store, never in `sdlc.config.yaml`, never in the step script. A gate that needs a secret names it by reference.
6. **Document the mapping** in the project README: gate → CI step → artifact name, so a red CI run is traceable to the same command the orchestrator runs.

## Gotchas

- **CI green ≠ review pass.** CI is G-script only; G-fresh stays a reviewer spawn. Never add an LLM call to CI to "auto-review" — nondeterministic, and it burns the reviewer's independence.
- **Do not fork gate definitions.** If CI needs a different command than `sdlc.config.yaml`, the config is wrong — fix the config, then CI inherits it. Two sources of gate truth = the config silently rots.
- **Main-branch discipline.** Feature branches may be mid-lane red on `--hat <future-stage>`; scope per-stage requires to the stages already done on that branch, and keep `--require` (whole-tree) for main.
- **No new gate kinds.** Coverage thresholds, security scanners etc. enter as `sdlc.config.yaml` commands first; CI just runs them.

## Self-check

- [ ] Every CI step maps 1:1 to a config/plugin command (no invented gates)?
- [ ] Exit codes passed through untranslated?
- [ ] Gate logs uploaded as artifacts in `gates[]`-admissible form?
- [ ] Secrets only by reference?
- [ ] Branch scoping: `--hat` per done stages on feature branches, full `--require` on main?
