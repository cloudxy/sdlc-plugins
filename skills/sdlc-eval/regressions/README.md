# Real-failure regression cases

Each JSON file compares an artifact an earlier plugin version produced on a real feature (baseline, "old") with what the current plugin produces from the same inputs and the same point in time ("new"), judged blind against a rubric. Run them with `/sdlc-eval regression <case-id|all>` (see `skills/sdlc-eval/SKILL.md` Step 4). Add new cases with `skills/sdlc-eval/templates/regression-case.md`.

| Case | Capability under test | Old artifact → judged as | New deliverables |
|---|---|---|---|
| R1-agents-market-pm | PM finds two-sided core value, core vs support, concepts, journeys | `01-define/spec.md` | spec, tracking, product strategy + feature map |
| R2-agents-market-design | Designer explores rendered directions, picks a defect-free, non-generic one | `02-shape/edge-states.md` | brief, directions, prototypes, flows, edge states, tokens, design system |
| R3-agents-market-architecture | Architect drives decisions with scenarios and options | `02-shape/contract.md` | contract, ADRs, contracts/, product architecture |
| R4-agents-market-dba | DBA models the domain and proves extensibility | `02-shape/db-spec.md` + `schema.dbml` | db-spec, DBML, product domain model + ERD |

Project root for these cases: the `auto_agents` repository (pass it with `--project-root`). Its `.sdlc` outputs were deleted from the working tree on 2026-09-17; the cases read inputs, old artifacts and hindsight documents from git at `artifacts_ref` (`2f256df`). Baseline: the last commit before 2026-09-15 (`c3fa226`, 2026-09-14); the feature directory and the later product layer (`docs/product`, `.sdlc/_product`) are hindsight. The "v3_gaps_observed" lines are grep-verifiable observations, not quality verdicts — the blind judges decide.
