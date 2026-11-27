---
name: "prototype"
description: "Use this skill when the spawn packet names prototype or $prototype. Do NOT load in /sdlc or as production evidence."
when_to_use: "Packet companion_skills includes prototype, or $prototype. Do NOT use from parent /sdlc or as production evidence."
---

# Prototype — disposable learning material that answers one question

Borrowed from mattpocock prototype. A discovery prototype is **disposable learning material that answers one falsifiable question**: a storyboard, sample input/output, UI variant probe, or minimal executable state model. The learning question selects the representation and whether execution is needed.

<!-- 来源（派生技能，只作追溯）：借鉴 mattpocock/skills skills/engineering/prototype；借鉴时的上游版本未记录，登记时上游为 mattpocock/skills@74ca5fe07745。已按本插件合同改写，上游变更不自动同步，也不放进 vendor/。 -->

Use it for discovery experiments (`discover` Falsify cheapest-test rungs 5–6) via the registered task `designer/market/prototype`, whose deliverable contract is `00-discover/prototypes/report.md` ([templates/prototype-report.md](templates/prototype-report.md)). The designer coordinates the experiment; request architect/developer help when the question is technical. Design directions (`02-shape/prototypes/D<n>/`) and the final handoff prototype (`02-shape/prototypes/final/`) are **not** throwaways — they follow `sdlc-workflow:design-contract`.

| Branch | Question it answers | Minimum representation ([references/branches.md](references/branches.md)) |
|---|---|---|
| **CONCEPT** | Do we understand the intended situation or workflow the same way? | Text storyboard, annotated flow, wireframe or sample input/output; no code required |
| **LOGIC** | Does this state machine, conflict rule or calculation feel right? | Minimal executable model: isolated reducer + HTML harness, CLI, or scratch script |
| **UI** | Which interaction/layout model fits an open visual question? | Distinct interaction sketches respecting accepted UX constraints (`≥44px` targets, clear state banner) |
| **FAKE** | Will target users take a costly intent action? | Local draft of fake door, waitlist or pricing concept — never exposed live without explicit operator authorization |

## Steps (step-by-step SOP)

1. **Pin the single question and constraints.** Read the packet's `question` and `constraints` inputs. Write down the exact decision this experiment unlocks, the time/effort budget, the predefined pass/fail or learning criterion, and sample/input limitations before building anything.
2. **Pick the cheapest valid branch (`CONCEPT | LOGIC | UI | FAKE`).** Consult [references/branches.md](references/branches.md). Never build an executable UI when an annotated storyboard (`CONCEPT`) resolves the ambiguity; never use a simulated UI (`UI`) to claim latency or throughput (`LOGIC`).
3. **Isolate in the scratch boundary.** Create all files strictly inside `00-discover/prototypes/<slug>/` (never touch production source directories or production databases). Use in-memory state by default; if persistence is the exact question, name the scratch file `PROTOTYPE-*`.
4. **Build only what tests the question — surface state explicitly.** Skip unrelated production abstractions, auth boilerplate and polish, while keeping enough honesty to answer the question (e.g., `LOGIC` renders the live state object after every action; `UI` renders a visible variant switcher + state banner and respects basic legibility/WCAG contrast so layout judgement is not distorted).
5. **Execute or verify honestly (`prepared` vs `observed`).** Bind actual check runs when testing logic/data; inspect screenshots via `scripts/ui-evidence.sh` when visual. If no real user has interacted or no live exposure was authorized, record status as `material-prepared (feedback pending)` — **never simulate user reactions or invent conversion numbers**.
6. **Capture the report and disposal plan.** Fill `00-discover/prototypes/report.md` from [templates/prototype-report.md](templates/prototype-report.md): record observed facts separately from simulated states, state what was learned (including negative/inconclusive results), return the delta for `00-discover/briefing.md`, and state the disposal rule (lift only the validated decision; prototype code never ships to production).

## Gotchas

- **Throwaway from day one.** Everything stays under `00-discover/prototypes/`; never import scratch files from `src/` or pass them off as `03-impl` evidence.
- **Wrong branch wastes the budget.** Shared mental model (`CONCEPT`), state rules (`LOGIC`), visual form (`UI`) and demand intent (`FAKE`) require different artifacts.
- **Observed ≠ simulated.** Keep observed execution/user facts strictly separate from mocked states. A local fake-door HTML file proves copy exists, not willingness to pay.
- **Real people & live traffic require explicit authorization.** Never publish a waitlist, send outreach, collect PII or charge money without recorded operator consent.
- **Do not ship the shell.** Even when a prototype succeeds, production implementation starts clean through `design-contract`, `architecture` and `impl-evidence`.

## Self-check

- [ ] Single falsifiable question, budget, pass/fail criterion, limits and disposal rule written first?
- [ ] Cheapest branch (`CONCEPT` / `LOGIC` / `UI` / `FAKE`) matches the uncertainty?
- [ ] All scratch files isolated under `00-discover/prototypes/`, zero production writes?
- [ ] State (`LOGIC`) or variant ID (`UI`) surfaced visibly; screenshots/runs actually inspected?
- [ ] `material-prepared` vs `observed` distinguished honestly; nothing exposed live without authorization?
- [ ] `00-discover/prototypes/report.md` completed with decision impact and non-promotion boundary?

## Deep references & templates — when to read them

| File | Read when… |
|---|---|
| [references/branches.md](references/branches.md) | Choosing `CONCEPT` vs `LOGIC` vs `UI` vs `FAKE` and minimum bar per branch |
| [templates/prototype-report.md](templates/prototype-report.md) | Writing `00-discover/prototypes/report.md` |
| [references/role-quality.md](references/role-quality.md) | Self-checking or reviewing discovery prototype rigor and honesty |
