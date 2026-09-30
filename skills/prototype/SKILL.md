---
name: "prototype"
description: "Use this skill when the spawn packet names prototype or $prototype. Do NOT load in /sdlc or as production evidence."
when_to_use: "Packet companion_skills includes prototype, or $prototype. Do NOT use from parent /sdlc or as production evidence."
---

# Prototype — learning material that answers one question

Borrowed from mattpocock prototype. A discovery prototype is **disposable learning material that answers a question**: a storyboard, sample input/output, sketch, or executable model. The learning question picks the representation and whether execution is needed.

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/engineering/prototype；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

Use it for discovery experiments (discover Falsify cheapest-test rungs 5–6) through the registered task `designer/market/prototype`, whose result contract is `00-discover/prototypes/report.md`. The designer coordinates the experiment; request architect/developer expertise when the question is technical. Design directions and the handoff prototype are not throwaways: they follow the direction-prototypes reference of `sdlc-workflow:design-contract`.

| Branch | Question | Shape |
|---|---|---|
| **CONCEPT** | Do we understand the intended situation or behavior the same way? | Text storyboard, annotated flow, wireframe or sample input/output; invite corrections without inventing user answers |
| **LOGIC** | Does this state model feel right? | Minimal executable model: HTML, CLI, notebook or scratch harness appropriate to the question |
| **UI** | What should it look like? | Distinct alternatives only when visual uncertainty is the question; reuse accepted constraints |
| **FAKE** | Will they want / pay? | Fake door, waitlist, or pricing page — no backend |

## Before building

The protocol task consumes `question` and `constraints`, both explicit files. It can finish independently as scoped work; a negative or bounded inconclusive result completes the exploration, not product implementation. Bind actual experiment checks where needed; an output report alone is not evidence that an experiment ran.

State at the top of the report: the one decision or question, the time/effort budget, the pass/fail or learning criterion, sample/input limitations, and the disposal or promotion plan.

Choose the least costly representation that can resolve the uncertainty. The manager may use an inline illustration during [discussion](../discover/references/discuss-protocol.md); a delegated prototype still follows the existing question/constraints/report contract. If no user has reacted or no experiment has run, report “material prepared / feedback pending”, not a validated finding. Agreement on a sketch clarifies understanding or preference; it does not prove demand, usability or performance.

## Gotchas

- **Throwaway from day one.** Path under `00-discover/prototypes/`; all code and data stay in that scratch directory, never production source by accident. Name it so a reader cannot mistake it for production.
- **Easy to inspect or run.** Concept material can be read directly; executable experiments use a simple entry point. No new top-level app just to clarify a flow.
- **No persistence by default.** Memory only, unless the question *is* persistence (scratch DB named PROTOTYPE).
- **Skip polish.** Use only validation needed to answer the question reliably; a concurrency/performance/data experiment may need a repeatable harness. Avoid production abstractions unrelated to the question.
- **Surface the state** (LOGIC) or the variant id (UI) after every action.
- **Do not ship the shell.** Lift only the validated decision. A promising prototype may inform a production design, but code promotion goes through normal implementation, security and verification review.
- **Wrong branch wastes the prototype.** Shared understanding, executable behavior, look and demand need different evidence.
- **Observed is not simulated.** Record observed results separately from simulated states. No fabricated conversion, latency or screenshots of a nonexistent production feature. A fake-door page does not establish willingness to pay without an appropriate observed action.
- **Real people need authorization.** Live exposure, messages or charges need the user's explicit authorization.

## Capture

Write preparation/execution status, actual observations (if any), unresolved questions and the decision supported into `00-discover/prototypes/report.md`; return the delta for briefing Discuss/Falsify as appropriate. Do not invent a learning verdict when only material is ready. Optional throwaway branch out of main.

## Self-check

- [ ] One question, budget, criterion, limits and disposal plan stated before building?
- [ ] Branch matches the question?
- [ ] Marked throwaway, kept in the scratch directory, not used as `03-impl` evidence?
- [ ] Observed and simulated results kept apart; nothing live without authorization?
- [ ] Verdict captured?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [branches.md](references/branches.md) | Choosing LOGIC vs UI vs FAKE and the minimum bar for each |
