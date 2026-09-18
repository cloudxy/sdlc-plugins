# Eval workspace layout

Sibling of the plugin directory (not inside `skills/`):

```
sdlc-workflow-eval-workspace/
  iteration-<N>/
    prd-gwt-<id>/
      with_skill/outputs/      # deliverable + optional transcript.md + screenshots
      without_skill/outputs/
      blind/                   # rubric mode: A/, B/ (normalized, memory/ removed), rubric.json, judgment.json (judge 1)
      blind-swap/              # same outputs, positions swapped (judge 2)
      blind-manifest.json      # files kept / dropped per arm — never shown to judges
    regression-<case-id>/
      snapshot/                # the project at the baseline commit (git archive) — the arm's read-only project root
      inputs/                  # copies of the case inputs
      old/outputs/             # the old artifact, at its deliverable path
      new/outputs/             # written by today's hat from task.md
      task.md                  # prompt for the new arm
      leak-markers.json        # hindsight fingerprints: baseline, later docs and code lines, later commits and files
      leak.json                # scan of new/outputs and of anything written into snapshot/
      leak-review.json         # the user's decision on leak suspects (only when asked)
      blind-manifest.json
      blind/  blind-swap/
    grading-<skill>.json       # scripts/grade_eval.py (mechanical)
    rubric-<skill>.json        # scripts/blind_eval.py aggregate (rubric / regression): verdict per case
    .blind-map-<skill>.json    # unblinding map — never shown to judges
```

One skill per iteration by default. Directory prefix is `<SKILL>-<id>` from the harness tables (v2 = 22 skills), or `regression-<id>`.
