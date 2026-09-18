---
name: "prototype"
description: "Use this skill when the spawn packet names prototype or $prototype. Do NOT use from parent /sdlc or as production evidence."
when_to_use: "Packet companion_skills includes prototype, or $prototype. Do NOT use from parent /sdlc or as production evidence."
---

# Prototype — throwaway that answers one question

Borrowed from mattpocock prototype. A prototype is **throwaway code that answers a question**. The question picks the branch.

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/engineering/prototype；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

Load as a companion (discover Falsify cheapest-test rungs 5–6, or a designer/general-purpose spawn). Capture the verdict in briefing; do not merge the shell to main as implement evidence.

| Branch | Question | Shape |
|---|---|---|
| **LOGIC** | Does this state model feel right? | One HTML file, buttons + visible state, no install |
| **UI** | What should it look like? | Several radically different variants, switchable |
| **FAKE** | Will they want / pay? | Fake door, waitlist, or pricing page — no backend |

## Gotchas

- **Throwaway from day one.** Path under `00-discover/prototypes/`. Name it so a reader cannot mistake it for production.
- **Trivial to run.** Double-click HTML or one project-runner command. No new top-level app.
- **No persistence by default.** Memory only, unless the question *is* persistence (scratch DB named PROTOTYPE).
- **Skip polish.** No tests, no extra abstraction, no error handling beyond runnable.
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
