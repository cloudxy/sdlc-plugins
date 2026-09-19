---
name: "prototype"
description: "Use this skill when the spawn packet names prototype or $prototype. Do NOT use from parent /sdlc or as production evidence."
when_to_use: "Packet companion_skills includes prototype, or $prototype. Do NOT use from parent /sdlc or as production evidence."
---

# Prototype — throwaway that answers one question

Borrowed from mattpocock prototype. A prototype is **throwaway code that answers a question**. The question picks the branch.

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/engineering/prototype；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

Load as a companion for discovery (discover Falsify cheapest-test rungs 5–6). Design directions and the handoff prototype are not throwaways: they follow the direction-prototypes reference of `sdlc-workflow:design-contract`. Capture the verdict in briefing; do not merge the shell to main as implement evidence.

| Branch | Question | Shape |
|---|---|---|
| **LOGIC** | Does this state model feel right? | Minimal executable model: HTML, CLI, notebook or scratch harness appropriate to the question |
| **UI** | What should it look like? | Distinct alternatives only when visual uncertainty is the question; reuse accepted constraints |
| **FAKE** | Will they want / pay? | Fake door, waitlist, or pricing page — no backend |

## Gotchas

- **Throwaway from day one.** Path under `00-discover/prototypes/`. Name it so a reader cannot mistake it for production.
- **Trivial to run.** Double-click HTML or one project-runner command. No new top-level app.
- **No persistence by default.** Memory only, unless the question *is* persistence (scratch DB named PROTOTYPE).
- **Skip polish.** Use only validation needed to answer the question reliably; a concurrency/performance/data experiment may need a repeatable harness. Avoid production abstractions unrelated to the question.
- **Surface the state** (LOGIC) or the variant id (UI) after every action.
- **Do not ship the shell.** Lift only the validated decision. Implement hats rewrite on the real lane.
- **Wrong branch wastes the prototype.** Logic vs look vs demand are different artifacts.

## Capture

When the question is answered: write the verdict + the question it settled into briefing § Falsify (or a note next to the prototype). Optional throwaway branch out of main.

## Self-check

- [ ] One question stated at the top of the prototype?
- [ ] Branch matches the question?
- [ ] Marked throwaway, not used as `03-impl` evidence?
- [ ] Verdict captured?

## Deep references — when to read them

| Reference | Read when... |
|---|---|
| [branches.md](references/branches.md) | Choosing LOGIC vs UI vs FAKE and the minimum bar for each |

## Registered experiment and limits

Use `designer/market/prototype` for a discovery experiment, with `00-discover/prototypes/report.md` as its result contract. The role coordinates the experiment; request architect/developer expertise when the question is technical. All code and data stay in the scoped scratch directory, never production source by accident. State one decision/question, time/effort budget, pass/fail or learning criterion, sample/input limitations and disposal/promotion plan before building.

Record observed results separately from simulated states. No fabricated conversion, latency or screenshots of a nonexistent production feature. A fake-door page does not establish willingness to pay without an appropriate observed action; live exposure, messages or charges require explicit authorization. A promising prototype may inform a production design, but code promotion requires normal implementation, security and verification review.
