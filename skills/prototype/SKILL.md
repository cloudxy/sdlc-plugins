---
name: "prototype"
description: "Use this skill when the spawn packet names prototype or $prototype. Do NOT use from parent /sdlc or as production evidence."
when_to_use: "Packet companion_skills includes prototype, or $prototype. Do NOT use from parent /sdlc or as production evidence."
---

# Prototype — throwaway that answers one question

Borrowed from mattpocock prototype. A prototype is **throwaway code that answers a question**. The question picks the branch.

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/engineering/prototype；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

Use it for discovery experiments (discover Falsify cheapest-test rungs 5–6) through the registered task `designer/market/prototype`, whose result contract is `00-discover/prototypes/report.md`. The designer coordinates the experiment; request architect/developer expertise when the question is technical. Design directions and the handoff prototype are not throwaways: they follow the direction-prototypes reference of `sdlc-workflow:design-contract`.

| Branch | Question | Shape |
|---|---|---|
| **LOGIC** | Does this state model feel right? | Minimal executable model: HTML, CLI, notebook or scratch harness appropriate to the question |
| **UI** | What should it look like? | Distinct alternatives only when visual uncertainty is the question; reuse accepted constraints |
| **FAKE** | Will they want / pay? | Fake door, waitlist, or pricing page — no backend |

## Before building

State at the top of the report: the one decision or question, the time/effort budget, the pass/fail or learning criterion, sample/input limitations, and the disposal or promotion plan.

## Gotchas

- **Throwaway from day one.** Path under `00-discover/prototypes/`; all code and data stay in that scratch directory, never production source by accident. Name it so a reader cannot mistake it for production.
- **Trivial to run.** Double-click HTML or one project-runner command. No new top-level app.
- **No persistence by default.** Memory only, unless the question *is* persistence (scratch DB named PROTOTYPE).
- **Skip polish.** Use only validation needed to answer the question reliably; a concurrency/performance/data experiment may need a repeatable harness. Avoid production abstractions unrelated to the question.
- **Surface the state** (LOGIC) or the variant id (UI) after every action.
- **Do not ship the shell.** Lift only the validated decision. A promising prototype may inform a production design, but code promotion goes through normal implementation, security and verification review.
- **Wrong branch wastes the prototype.** Logic vs look vs demand are different artifacts.
- **Observed is not simulated.** Record observed results separately from simulated states. No fabricated conversion, latency or screenshots of a nonexistent production feature. A fake-door page does not establish willingness to pay without an appropriate observed action.
- **Real people need authorization.** Live exposure, messages or charges need the user's explicit authorization.

## Capture

When the question is answered: write the verdict and the question it settled into `00-discover/prototypes/report.md` and briefing § Falsify. Optional throwaway branch out of main.

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
