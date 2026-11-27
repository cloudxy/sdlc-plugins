# Algorithm Role Quality — Expert Bar vs Mediocre Order-Taker

Shared quality criteria for `algo` producers and `reviewer` / `qc` independent reviews.

## Expert Bar (Pass)
1. **Frozen, versioned evaluation oracle**: Every quality claim names a concrete `eval-set-v<n>` snapshot ID, stratified failure/edge slices, labeling criteria, and an untouched held-out test split.
2. **5-anchor reproducibility**: Seed/temperature, dependency lockfile, dataset snapshot ID, prompt/pipeline config SHA-256, and runtime/model snapshot ID are recorded verbatim.
3. **Cheapest baseline & single-variable rigor**: Rules/prior baseline runs on the exact same split; each candidate changes one variable and reports accuracy alongside P95 latency and unit cost.
4. **Fail-closed bounds & degradation**: `max_steps`, retries, token/size caps, split timeouts, tenant/ACL retrieval filters, and 3-tier fallback (`primary -> backup -> deterministic/abstention`) are enforced outside prompts and exercised under fault simulation.
5. **Honest scope separation**: Mocked runs are labeled as contract checks only; `explore`/`evaluate`/`diagnose` make zero unauthorized production code edits.

## Mediocre Order-Taker (Reject / Finding)
- Reporting "improved accuracy" from 3 cherry-picked examples or tuning on the test split (Dimension 3 / 6 `major`).
- Treating field non-empty rate or mocked JSON responses as proof of model quality (Dimension 3 `major`).
- Omitting tenant/ACL retrieval filters, unbounded tool loops, or silent fallback on corrupted context (Dimension 4 / 5 `blocker`).
- Mixing business CRUD or UI changes into an `algo` slice without delegated scope (Dimension 1 `major`).
