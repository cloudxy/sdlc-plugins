---
name: debug
description: "Use this skill when the spawn packet selects diagnose or attaches debug_protocol, or $debug. Do NOT use to define new product behavior."
when_to_use: "Spawn packet carries debug_protocol, or $debug. Do NOT use from parent /sdlc or for anything other than locating a defect's mechanism."
---

# Debug — locate the mechanism from first-hand evidence, then fix the minimum

Procedure for **technical diagnosis** (`implement/diagnose`, `collect/diagnose`) and rework rounds carrying `debug_protocol`. The producing hat keeps its identity and primary procedure skill; this skill governs how to bisect failure mechanisms without guesswork. Manager-side loop rules live in the orchestrator — do not read them; your packet's task or `debug_protocol` is your instruction.

A repeated gate failure is a **hypothesis problem, not an effort problem**. Re-running the same command hoping it turns green is a bare retry — forbidden.

## Independent diagnosis (`04-verify/diagnosis-<role>.md`)

For `backend`, `frontend`, `algo`, or `miner` `implement/diagnose` and `collector` `collect/diagnose`, the stopping point is an evidence-backed report written with [templates/diagnosis.md](templates/diagnosis.md) to `04-verify/diagnosis-<role>.md` (including a bounded `inconclusive` outcome when environment/access limits block certainty). Consume the symptom and accepted behavior/eval baseline. **Do not edit production source or perform steps 4–5** unless a separate repair task (`implement/fix` or rework ticket) authorizes source writes.

A diagnostic probe/script may exit `0` when it successfully demonstrates the bug: label that result **`reproduction confirmed`**, never **`bug fixed`**. Keep raw failing output and ruled-out probes. In live customer incidents, authorized operational mitigation proceeds first under `deliver` authority — root-cause diagnosis never delays urgent mitigation.

## The loop (in order, targeted probes only — full-suite test runs forbidden)

1. **Reproduce.** Run one **targeted** command + exit code showing the failure verbatim. For UI consistency or functional equivalence claims, static SVG/CSS/code diffs do **not** reproduce behavior: exercise `click -> observe` on each control. Cannot reproduce → report exact attempts, mark `reproduction unavailable`, inspect read-only logs/traces/stores, and bound hypotheses without fabricating a cause.
2. **Isolate with first-hand probes.** Bisect the path until one smallest trigger remains. Connect read-only to the actual DB/Redis/queue/DOM before inventing theories; use conservation checks (`Σ detail == total`) and failure-set stability to cut the search space in half. Record every eliminated hypothesis as: `hypothesis -> probe -> result`. Remove any temporary probe or rejected patch immediately — never stack fixes over failed guesses.
3. **Name the mechanism & confidence.** State the structural or temporal **mechanism** (e.g., "Router imports ORM and triggers lazy load post-commit", "module-level permission `dict` lost across worker 2 / F5 reload", "gateway read timeout `In-Doubt` treated as `Fail` causing duplicate charge", "GWT oracle contradicts FR-3"), never the symptom ("test failed", "500 error"). Separate `confirmed`, `suspected`, `ruled out`, and `unknown`.
4. **Minimal fix (authorized repair tasks only).** Touch only the smallest seam implied by the confirmed mechanism. Zero drive-by refactors or unrelated cleanups in a rework round.
5. **Re-run the exact failed gate/reproduction.** Paste verbatim output + exit code. For flaky failures, run repeated targeted iterations / deterministic clock or concurrency barriers — a single passing retry never proves a flaky race is fixed.
6. **Record & return.** Append `## Debug record` to `impl-evidence.md` (or write [templates/diagnosis.md](templates/diagnosis.md) for standalone `diagnose`) and return `root_cause: <confirmed mechanism | unverified: best hypothesis + next discriminating probe>`.

## High-leverage diagnostic lenses & gotchas

- **Stability of the failure set splits semantics from timing.** Identical records failing every run → **semantic/contract bug** (routing, SQL predicate, `get(field, [])` collapsing `missing` with `empty`, tenant/scope filter). Varying records across runs → **temporal/concurrency/state bug** (multi-worker process-local `dict`/`RLock`, stale async response race, listen/TTL window, `In-Doubt` timeout).
- **Check multi-worker Statelessness & Three-State `In-Doubt` traps.** Code passing single-process tests fails in production when mutable state lives in Python/Node globals across workers, or when an external timeout (`In-Doubt`) triggers an unkeyed retry or rolls back local state after remote execution succeeded.
- **First-hand store inspection beats fluent narratives & prior changelogs.** "Fixed X" in an earlier commit only shows what was tried. An operator report ("only 2 keys exist") can be a UI pagination cap while all rows sit in storage — query read-only first.
- **UI geometry, focus & pointer chains require live state capture.** A stray line may be `:focus-visible` on a host container coexisting with a progress bar; a visible menu item can still fail to fire when `focusout`/`blur` hides the node before `click` lands. Inspect active element, bounding boxes, computed styles, and real pointer/focus event order.
- **Never edit GWT, `schema.dbml`, coverage matrices, or design tokens to make a red gate disappear.** Oracle defects route to `pm`, `dba`, or `designer` via `open_questions`; business/aesthetic disagreements are owner decisions, not shell bugs. Fix one mechanism per round; park secondary bugs in `open_questions`.

## Self-check & review

Apply [references/role-quality.md](references/role-quality.md) alongside this checklist:

- [ ] Verbatim targeted reproduction (or explicit `reproduction unavailable` + probes) recorded before any edit, including live `click -> observe` for UI equivalence claims?
- [ ] Every ruled-out hypothesis logged as `hypothesis -> probe -> result`, with zero leftover speculative edits?
- [ ] `root_cause` names a concrete mechanism with honest confidence bounds (never a bare symptom or fabricated certainty)?
- [ ] Standalone `diagnose` wrote [templates/diagnosis.md](templates/diagnosis.md) with zero production edits; repair tasks touched only the minimal seam and re-ran the exact failing gate verbatim?
- [ ] GWT, schema, coverage matrix, and tokens untouched; secondary issues parked in `open_questions`?
