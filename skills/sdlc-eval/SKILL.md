---
name: sdlc-eval
description: "Use this skill when the user says /sdlc-eval. Do NOT use from parent /sdlc or as a substitute for check-sdlc.sh."
when_to_use: "Use this skill when the user says /sdlc-eval or names the eval harness (including rubric judging or regression runs). Do NOT use from parent /sdlc. Do NOT use for weekly maintenance, health-check, a 19-role sweep, or as a substitute for check-sdlc.sh."
---

# SDLC eval harness (v2 = mechanical hygiene + blind rubric judging + real-failure regressions)

This window is the **manager**. You orchestrate **one human-triggered eval pass**. You do not wear any hat and you never judge outputs yourself.

**Why v2.** The v1 grader (`grade_eval.py`) is keywords and regexes. It proves hygiene — refusals, required phrases — and cannot tell whether a spec finds the core value, a design direction is memorable, or a schema survives the roadmap. Optimizing the plugin against it produced compliant, mediocre artifacts. v2 keeps the mechanical grade as a floor and adds what decides quality: **blind rubric judging** by fresh judges, and **regressions on real past runs** (old artifact vs today's output).

| Mode | Question it answers | Scripts |
|---|---|---|
| `mechanical` (default) | Does the skill keep its hygiene rules? | `grade_eval.py` |
| `rubric` | Is the with-skill output actually better than a capable baseline on the dimensions that matter? | `blind_eval.py prepare / aggregate` |
| `regression` | On a real feature that went badly, is today's plugin output better than what it produced then? | `blind_eval.py regression-prepare / prepare --regression / aggregate --skill regression` |

## Harness tables (22 skills)

Delivery:

| --skill | with_skill arm (hat) | cases |
|---|---|---|
| `prd-gwt` | `sdlc-workflow:pm` | all |
| `findings` | `sdlc-workflow:reviewer` | `1`, `4` by default; user may name others |
| `coverage-matrix` | `sdlc-workflow:qa` | first 2 + rubric cases |
| `impl-evidence` | `sdlc-workflow:frontend` | `ui-1`, `ui-5` |
| `debug` | `sdlc-workflow:frontend` + packet line `debug_protocol: <PLUGIN_ROOT>/skills/sdlc/references/debug-loop` | all |
| `tdd` | `sdlc-workflow:backend` + packet line `companion_skills: [tdd]` | all |
| `refactor` | `sdlc-workflow:backend` (ticket marked maintenance) | all |
| `cicd` | `sdlc-workflow:sre` | all |

Product, design, data (added in v2 — previously never evaluated):

| --skill | with_skill arm | cases |
|---|---|---|
| `design-contract` | `sdlc-workflow:designer` | all |
| `schema` | `sdlc-workflow:dba` | all |
| `growth` | `sdlc-workflow:growth` + packet `stage` from the case prompt | all |
| `collect` | `sdlc-workflow:data-collector` (tracking cases: `sdlc-workflow:pm` + `companion_skills: [collect]`) | `tracking-1`, `tracking-2` by default |
| `warehouse` | `sdlc-workflow:data-warehouse-engineer` | all |
| `release-gate` | `sdlc-workflow:qc` | all |

Discovery / ops:

| --skill | with_skill arm | cases |
|---|---|---|
| `discover` | `general-purpose` + PLUGIN_ROOT + follow `skills/discover/SKILL.md` | all |
| `market` | `sdlc-workflow:researcher` | all |
| `compete` | `sdlc-workflow:competitor` | all |
| `falsify` | `general-purpose` + PLUGIN_ROOT + follow `skills/falsify/SKILL.md` | all |
| `enablement` | `sdlc-workflow:ops` + packet `stage: enablement` `primary_skill: sdlc-workflow:enablement` | all |
| `signals` | `sdlc-workflow:ops` + packet `stage: signals` `primary_skill: sdlc-workflow:signals` | `1`, `5` |

Orchestration:

| --skill | with_skill arm | cases |
|---|---|---|
| `architecture` | `sdlc-workflow:architect` | all |
| `sdlc` | `general-purpose` + PLUGIN_ROOT + follow `skills/sdlc/SKILL.md` | `1`, `2` by default; user may name others |

## Gotchas

- **This is not a gate.** Do not add it to scheduled maintenance or `health-check.sh`. It burns real model calls and is non-deterministic.
- **Scope = the rows above.** Refuse a 19-role sweep or skills not in the tables.
- **Baseline is `general-purpose`.** That is the without-skill arm, not a role spawn. Do not invert.
- **Do not paste SKILL.md** into any spawn prompt. with_skill gets PLUGIN_ROOT; without_skill must not read it.
- **Spawn all arms of one skill in one turn** (fresh context each), and all judges of one skill in one turn.
- **You never judge.** Neither you nor the producing arms score outputs. Judges are fresh `general-purpose` spawns that see only one blind folder; the unblinding map (`.blind-map-*.json`) is never in a judge prompt.
- **Two judges per case, positions swapped** (`blind/` and `blind-swap/`) — LLM judges favour position and length; the swap and the scale anchors counter that. Disagreement between the two judges is information: read both rationales.
- **Judgments are machine-checked.** Every score must quote its own side verbatim (「…」) or cite an image on its own side; the inventory must list the side's documents; a verified defect caps its criterion at 3. `validate` / `aggregate` reject paraphrases, skipped documents and quotes found only on the other side (suspected A/B swap). An unchecked judge once credited side A with side B's spec.
- **A judge's claim is a lead, not a finding.** Before a rationale becomes a plugin change, open the cited file on the cited side and map the side to its arm. 2026-09-17: a swapped judgment was turned into a false "PM mixes spec versions" fix.
- **A rubric delta is evidence, not proof.** Report scores with the judges' rationales and the number of cases; one case is an anecdote.
- **Regressions run in the past.** The arm works in `snapshot/` (the project at the baseline commit), never in the live repository: at HEAD the old design is already built, reviewed and fixed, and copying it is hindsight. The leak scan decides — INVALID is never judged; REVIEW is the user's call, not yours.
- **Judges see deliverables only.** Blind copies drop the `.sdlc/<feature>/` prefix and keep only the case's deliverables (skill mode: everything except memory/ and product-delta.md), so a side cannot be recognized by its folder layout.

## Plugin root and workspace

This file is `<plugin>/skills/sdlc-eval/SKILL.md`; PLUGIN_ROOT is two directories up (prefer `$ZCODE_PLUGIN_ROOT`). Workspace = sibling folder `sdlc-workflow-eval-workspace/` ([templates/run-layout.md](templates/run-layout.md)). Next iteration = max existing + 1.

## Step 0 — refuse or init

If the user asks for all roles, cron, or health-check integration → refuse with the Gotchas, stop. Else pick the mode (`mechanical` default; `rubric` when the user asks for quality / judging or the skill's cases carry `rubric`; `regression` when they name a regression case or "真实案例回归"), the skill (from the tables) and the case set. Create `<workspace>/iteration-<N>/<SKILL>-<id>/{with_skill,without_skill}/outputs/` for each case.

## Step 1 — the arm spawns (same turn)

**with_skill** — `subagent_type` from the table:

```
Task: <case.prompt>
Deliverable path: <abs>/<SKILL>-<id>/with_skill/outputs/
PLUGIN_ROOT: <PLUGIN_ROOT>
<Packet trigger line if the table names one>
Do not spawn further subagents.
Write the deliverable into the deliverable path. For UI or visual work, render and save screenshots there too. Return that path + short summary.
```

**without_skill** — `subagent_type: "general-purpose"`:

```
Task: <case.prompt>
Deliverable path: <abs>/<SKILL>-<id>/without_skill/outputs/
Do not read PLUGIN_ROOT. Do not invoke any sdlc-workflow skill. Do not spawn further subagents.
Write your answer into the deliverable path. Return that path + short summary.
```

If an arm wrote nothing, write `outputs/transcript.md` from its final message.

## Step 2 — mechanical grade (always)

```
python3 <PLUGIN_ROOT>/scripts/grade_eval.py --plugin-root <PLUGIN_ROOT> --workspace <workspace> --iteration <N> --skill <SKILL> [--cases <ids>]
```

Show the table. Mechanical fail stays fail; skip is not pass.

## Step 3 — blind rubric judging (mode rubric, cases with a `rubric`)

1. `python3 <PLUGIN_ROOT>/scripts/blind_eval.py prepare --workspace <workspace> --iteration <N> --skill <SKILL> [--cases <ids>]`
2. For **every** folder it prints (`…/blind` and `…/blind-swap`), spawn one fresh `general-purpose` judge in the same turn, prompt = [templates/judge-packet.md](templates/judge-packet.md) (v2) with the folder path filled in. Nothing else — no arm names, no map, no manager opinion.
3. `python3 <PLUGIN_ROOT>/scripts/blind_eval.py aggregate --workspace <workspace> --iteration <N> --skill <SKILL>`
4. Exit 3 = a judgment failed validation. Respawn only that judge once, with the packet plus its problem lines. Still invalid → the case stays `INVALID (judgments)`; never fill in scores yourself.
5. Report per case: verdict (PASS / FAIL / SPLIT / INVALID), weighted scores, `criterion_delta`, the weakest criteria of the with-skill arm, and two or three judge rationales — each claim you repeat checked in the cited file first.

## Step 4 — real-failure regressions (mode regression)

Cases live in `PLUGIN_ROOT/skills/sdlc-eval/regressions/*.json` (fields: [templates/regression-case.md](templates/regression-case.md)). Each names a real artifact produced by an earlier plugin version, the time before that work started, the inputs, the deliverables and a rubric.

1. Ask for (or reuse) the project root, then per case: `python3 <PLUGIN_ROOT>/scripts/blind_eval.py regression-prepare --workspace <workspace> --iteration <N> --case <case.json> --project-root <project>`. It exports the project at the baseline commit into `regression-<id>/snapshot/`, copies inputs and the old artifact, fingerprints hindsight and writes `task.md`. It never writes to the project; `--force` discards an earlier arm's outputs.
2. Spawn each case's hat (`subagent_type: sdlc-workflow:<hat>`) with its `task.md` as the prompt, all cases in one turn. Prefer a session whose working directory is not the live project. The arm writes only to `new/outputs/`.
3. `python3 <PLUGIN_ROOT>/scripts/blind_eval.py prepare --workspace <workspace> --iteration <N> --regression <case.json>` scans for leaks before it blinds anything:
   - **exit 4 = INVALID (leak).** Do not judge. Show the user the hits, then `regression-prepare --force` and re-run that arm.
   - **REVIEW (one or two later file names).** Show the user each hit (file:line and text) and ask whether the name follows from the task or inputs. Record their words: `blind_eval.py leak-review --workspace <workspace> --iteration <N> --case <id> --decision clear|reject --reason "<user's words>"`. Never decide it yourself.
   Then two judges per case (Step 3.2) → `aggregate --skill regression` (Step 3.4 for invalid judgments).
4. Verdicts: **PASS** = both valid judges prefer new and no criterion's mean drops · **FAIL** · **SPLIT** = judges disagree · **REVIEW** = leak suspects undecided · **INVALID** = leak or judgments. Only PASS / FAIL / SPLIT are counted. Report old vs new per criterion together with each case's leak status.

## Baseline discipline (5A)

Before merging a change to a role profile, skill or protocol: run the affected skill in `rubric` mode (and the related regression cases) before and after; keep both iterations; the delta and the rationales are the evidence. Without a historical baseline, the without-skill arm is the baseline.

## Self-check

- [ ] Arms of one skill spawned in one turn; with_skill uses the table's hat; without_skill is general-purpose?
- [ ] `grade_eval.py` ran (mechanical floor)?
- [ ] Rubric mode: two blind judges per case (blind + blind-swap), judges saw only their folder, `aggregate` exited 0 or invalid judges were respawned once?
- [ ] Regression mode: arms worked in `snapshot/` from `regression-prepare`; the leak scan ran; no INVALID case was judged; every REVIEW decision is the user's, recorded with `leak-review`?
- [ ] Reported verdicts and rationales, not just numbers; every judge claim repeated was checked in the cited file; no judging in this window?
- [ ] Did not touch health-check or crontab?
