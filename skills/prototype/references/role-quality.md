# Discovery Prototype Quality Rubric (`prototype`)

Both the producing specialist (`designer`, with technical input when needed) and `reviewer` judge discovery prototypes against this bar. Mistaking prototype code for production readiness, or reporting simulated states as observed evidence, is a **blocker/major** finding.

## Expert Bar vs. Mediocre Order-Taker

| Dimension | Expert Prototyper | Mediocre Order-Taker (Reject) |
|---|---|---|
| **Question & Branch Fit** | Isolates one falsifiable question and picks the cheapest valid branch (`CONCEPT` storyboard, `LOGIC` state reducer, `UI` interaction contrast, `FAKE` intent draft) | Builds a 1,500-line mini React app with login/settings when a 5-step storyboard or 40-line state harness would answer the question |
| **Pre-Registered Criterion** | States pass/fail or learning criterion, input limitations and timebox *before* building; reports negative/killed findings cleanly | Retrofits "prototype looks great, hypothesis validated" after building a happy-path demo |
| **Honest Evidence (`Prepared` vs `Observed`)** | Explicitly labels unshown drafts as `material-prepared (feedback pending)`; separates deterministic harness runs from mocked UI numbers; never exposes `FAKE` doors live without operator consent | Claims "users preferred Variant B" or quotes latency/conversion numbers from hardcoded mock JSON |
| **State Visibility & Ergonomics** | `LOGIC` exposes the authoritative state transition after every action (catching illegal states/edge clashes); `UI` surfaces variant IDs and respects basic contrast/target legibility so feedback reflects structure, not broken CSS | Hides state inside opaque click handlers; renders broken mobile layouts that confound user reactions |
| **Isolation & Disposal Discipline** | Keeps 100% of scratch code/data inside `00-discover/prototypes/`, documents what *decision* transfers to `briefing.md` / `spec.md`, and explicitly forbids promoting scratch code to `src/` or `02-shape/prototypes/final/` | Writes into repository `src/`, creates production DB tables, or reuses throwaway prototype screenshots as `02-shape` final contract or `03-impl` build evidence |

## Core Principles

1. **Minimum Cost to Truth (YAGNI):** Every line of code that does not sharpen the answer to the stated question is waste and anchors the team to a premature solution.
2. **State Isomorphism in `LOGIC`:** Keep state transitions pure (`nextState = step(state, action)`) and visible on screen so stakeholders spot broken domain rules in seconds.
3. **Strict Evidence Firewall:** Discovery prototypes validate *understanding, state feel or experiment readiness*; they never substitute for `design-contract` handoff prototypes or running-build verification.

## Second-Order Scan (Before Delivery)

- **Anchoring Trap:** Did the prototype accidentally bake in unapproved pricing, permissions or architecture choices as if they were settled? List them as open questions in `report.md`.
- **Contamination Check:** Are `git status` and `source_writes` completely clean outside `00-discover/prototypes/`?
- **Decision Handoff:** Reading `00-discover/prototypes/report.md` alone, can `discover` / `pm` immediately update `briefing.md § Falsify` without guessing whether an experiment actually ran?
