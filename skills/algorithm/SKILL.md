---
name: "algorithm"
description: "Use this skill when the spawn packet names algo or $algorithm. Do NOT load in /sdlc or for business CRUD or UI."
when_to_use: "Spawn packet names hat algo or user invokes $algorithm. Do NOT use from parent /sdlc or for business CRUD, OLTP schema, or frontend UI."
---

# Algorithm — measurable, bounded, degradable AI/ML/ranking engineering

Job: **turn AI, ML, RAG, ranking, prompt, and scoring work into reproducible, versioned, bounded systems** — an algorithm or prompt change without a pinned evaluation set is flying blind.

## Tasks (registered under `algo`)

| Task | Scope & deliverable |
|---|---|
| `implement/explore` | Feasibility, cheapest baseline, initial stratified `eval-set-v<n>`, and cost/latency ceiling (`03-impl/algo-explore-evidence.md`) |
| `implement/evaluate` | Frozen-split benchmark comparing candidates on identical `eval-set-v<n>` with latency & cost ledger (`03-impl/algo-evaluate-evidence.md`) |
| `implement/T-<n>` | Production AI/ML/ranking slice inside scoped `source_writes` with bounded runtime, 3-tier fallback, and slice integration (`03-impl/T-<n>-algo-evidence.md`) |
| `implement/diagnose` | Read-only badcase/drift/retrieval isolation (uses `debug`, `04-verify/diagnosis-algo.md`) — zero production source edits |
| `implement/fix` | Scoped regression/badcase fix inside `source_writes` with reproduction fix + non-regression across stratified splits (`03-impl/fix-algo-evidence.md`) |

## Gotchas & engineering red lines

- **No eval-set version = meaningless score.** Never report accuracy/recall without naming the frozen `eval-set-v<n>` snapshot ID; never tune prompts on the held-out test split.
- **Mocked model calls test contracts, never quality.** Use mocks for schema/SSE/retry plumbing; quality claims come only from versioned evaluation runs.
- **5-anchor reproducibility lock.** Record seed/temperature, dependency lockfile, pinned dataset snapshot ID (never `"latest"`), prompt/config SHA-256, and runtime/model snapshot ID.
- **Bounded everything & fail-closed context.** Enforce hard `max_steps`, `max_tool_retries`, input/output caps, split timeouts, daily spend caps, and tenant/ACL filtering **outside** the prompt; treat external/tool timeouts as `In-Doubt` and validate 3-tier fallback (`primary -> backup -> deterministic rules / honest abstention`).
- **One variable per iteration.** Compare against the cheapest baseline first; keep proxy metrics (non-empty rate) separate from real task accuracy, and pre-register online decision metrics (1 primary + ≤3 guardrails) before exposure.
- **Keep scope proportional.** Reuse pinned data/baselines from the brief; do not build heavy custom harnesses for single-metric checks, and stop after at most one factual fix pass once declared checks pass.

## Self-check

- [ ] Pinned `eval-set-v<n>` snapshot ID, labels, and held-out split preserved?
- [ ] All 5 reproducibility anchors recorded; cheapest baseline compared on identical split?
- [ ] Hard runtime bounds, fail-closed context/ACL checks, and 3-tier degradation verified?
- [ ] Only scoped `source_writes` modified (none for `explore`/`evaluate`/`diagnose`), with exact commands and exit codes?

## Deep references — load only when needed

- Shared role criteria: [references/role-quality.md](references/role-quality.md)
- Detailed AI/RAG/eval playbooks & templates: [../impl-evidence/references/ai.md](../impl-evidence/references/ai.md)
