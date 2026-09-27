# Controlled comparisons

`comparison` identifies the question: `plugin` for the plugin combination, `skill` for one method, `chain` for upstream effects on a fixed downstream process. `scope: role_task` cannot support whole-workflow claims; `scope: workflow` requires a plugin case containing actual manager decisions, handoffs and gates. `treatment: with_without` asks whether a method helps; `old_new` compares a frozen old method with the current one. A without baseline cannot substitute for old_new when claiming this revision improved quality.

Use the deterministic setup before spending an agreed model-call budget:

```sh
python3 PLUGIN_ROOT/scripts/workflow.py eval-prepare --spec /absolute/spec.json --out /absolute/YYYY-MM-DD-case-unique
python3 PLUGIN_ROOT/scripts/workflow.py eval-audit --run /absolute/generated-eval-manifest.json --observations /absolute/host-observations.json
python3 PLUGIN_ROOT/scripts/workflow.py eval-blind --run /absolute/generated-eval-manifest.json --observations /absolute/host-observations.json
```

The strict spec fields are comparison, treatment, scope, role, stage, concrete task, case, model, settings, tools, budget, plugin_new, contract_version (1), seed; skill comparisons also specify skill, old_new requires plugin_old. Budget contains positive calls/output_tokens/seconds. Case contains id, prompt, fixture_root, explicit inputs, explicit deliverables and the existing weighted rubric format. Use [../evals/round2-cases.json](../evals/round2-cases.json) and its runnable fixtures as pilot inputs; they are not completed model runs. Retain separate held-out cases when deciding whether a method rewrite generalizes.

Chain adds two or more steps, each with role/stage/task/consumes/produces. Only step 1's method varies; later methods are copied from the same plugin_new snapshot in both arms. Schedule each step in a fresh session with equivalent model/tools/budget and give the next step the actual preceding output. PM → QA test-plan and architecture contract → backend are different experiments; the latter does not test conformance. Source checks and final artifact criteria stay fixed.

The setup writes independent project copies and the same neutral role preamble from a source whitelist (role/function, ownership, common output/authority constraints). It does not edit a full generated agent: method instructions in Identity, Assignments, Loop, Skills, Contract or indirect references would otherwise contaminate the control. Both arms use the same host execution type and actual tool permissions. Reading a method explicitly is a content test when native Skill loading cannot be held equal; report production routing smoke separately.

An observation document maps each arm (`without/with` or `old/new`) to model/settings/tools/calls/reads/method_loads/complete_trace. These are host observations, not producer recollections. Missing or incomplete traces, unequal tools, control method loading or reads outside the isolated arm invalidate the controlled comparison. Preparation merely declares tools; it does not prove host equivalence or enforce isolation. Use host traces or an isolated work environment; absent capabilities stay unverified. Do not fill the observation document with guessed reads.

Only after a valid audit, eval-blind creates blind and blind-swap folders in the existing rubric/judgment format. Give each fresh judge only its folder and the existing judge packet. Run `blind_eval.py validate --folder ...` for each. The private dated map records true arm labels, comparison and treatment; never pass it, run records, method reports or state to judges. Preserve every failed/invalid/unrun case. `grade_eval.py` remains method-specific hygiene: its named-section/keyword requirements are not a neutral business-quality score for the control.

Report criterion-level defects and both judge rationales, exact case count, treatment/scope, unresolved blocking clarifications (deduplicate by the underlying decision and blocked consumer), rework (from failed acceptance to verified correction), downstream usability and actual resource use. Necessary questions can improve quality. Use host token/time measurements or unavailable; do not substitute an estimate silently. With no authorized budget or no trace-capable host, complete fixtures/mechanical validation and leave quality acceptance pending. No automatic sweep or scheduled model evaluation is added.
