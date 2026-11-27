# How to add a real-failure regression case

A regression case turns a feature that went badly into a permanent test: the **old artifact** the plugin produced then vs the **new output** the current plugin produces from the same inputs **and the same knowledge**, judged blind against a rubric.

## When to add one

- A stakeholder said an artifact was poor ("PM missed the core feature", "design had no highlight", "schema needed a rewrite two features later").
- A post-launch retro traced a problem back to a define / shape artifact.
- A gate or reviewer caught something only after rework ≥ 2.

## File: `skills/sdlc-eval/regressions/<id>.json`

```json
{
  "id": "R5-<feature>-<role>",
  "title": "<一句话：这个案例检验什么能力>",
  "project": "<project name, informational>",
  "skill": "<primary skill, e.g. schema>",
  "hat": "<spawn role, e.g. dba>",
  "stage": "<stage-id, e.g. dba>",
  "baseline_before": "<ISO time just before the old feature work started, e.g. 2026-09-15T00:00:00+08:00>",
  "artifacts_ref": "<commit that still contains the inputs and the old artifact>",
  "exclude_paths": ["<project paths removed from the snapshot, e.g. .sdlc/<feature>>"],
  "hindsight_paths": ["<working-tree paths written later that the arm must not know, e.g. docs/product>"],
  "inputs": ["<project paths the old artifact was made from>"],
  "baseline": [{"from": "<project path of the old artifact>", "as": "<deliverable path it competes with>"}],
  "product_root": "product",
  "deliverables": ["<paths or globs under new/outputs that are judged, e.g. 02-shape/db-spec.md, product/erd.dbml>"],
  "leak_markers": ["<optional: strings that exist only after the baseline, e.g. a later finding id>"],
  "task": "<the natural instruction the hat gets — same kind of request as originally, not a hint list>",
  "v3_gaps_observed": ["<verifiable observations about the old artifact, with how you checked>"],
  "what_good_looks_like": "<short description for the judge; describe qualities, not the answer>",
  "rubric": [
    {"id": "<snake_id>", "criterion": "<one observable quality>", "weight": 1}
  ]
}
```

`baseline_commit` may replace `baseline_before`. `artifacts_ref` lets the case keep working after the project deletes its `.sdlc` outputs: inputs, the old artifact and hindsight documents missing from the working tree are read from git at that commit. Omit `product_root` when the stage writes no product files; `leak_markers` and `hindsight_paths` are optional.

## Rules

- **The arm works in the past.** `regression-prepare` exports the project at the last commit before `baseline_before` (git archive, read-only) and removes `exclude_paths`. Pick the moment before the old feature work began (state.yaml, the first dated artifact) — not today's tree, where the old design is already implemented, reviewed and fixed. A run at HEAD is hindsight, not a regression (2026-09-17: two of four arms documented the already-built schema and named test files that did not exist yet).
- **Hindsight is fingerprinted.** The baseline artifact, everything under `exclude_paths` and `hindsight_paths`, lines added to the repo after the baseline, later commit ids and later numbered migrations become markers. A verbatim hit makes the case INVALID; three or more later file names do too; one or two are REVIEW for the user.
- **Deliverables make the sides comparable.** Map each old artifact to the deliverable path it competes with (`as`), and list the product-layer files today's procedure writes at that stage. Judges see only deliverables: memory/ and product-delta.md never reach them.
- **Task is neutral.** Do not paste the rubric into the task; the plugin's skills must produce the quality on their own.
- **Gaps are verifiable.** "grep 核心价值 → 0 matches" beats "the spec was bad".
- **Criteria must not punish obeying an operator decision.** When the inputs record one (e.g. K3 kept a side out of acceptance), word the criterion so honoring it scores well and only the missing craft scores low.
- **Visual cases judge the pick, not only the spread.** Include a criterion for defects in the recommended direction's own screenshots and one for generic AI-default styling.
- **Rubric = 4–6 criteria**, each one observable quality, weights 1–3, the most important weighted highest.
- **Inputs must predate the baseline.** Do not give the new arm artifacts that were written after (or because of) the old one.
- **No secrets.** If inputs contain credentials or personal data, redact copies before using the case.
- Paths are relative; the project root is passed at run time (`--project-root`), never hardcoded.
