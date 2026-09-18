---
name: "design-contract"
description: "Use this skill when the spawn packet names hat designer or $design-contract. Do NOT use from parent /sdlc or for frontend code."
when_to_use: "Spawn packet names designer (task explore / specify / design-qa), or $design-contract. Do NOT use from parent /sdlc. Do NOT use for frontend implementation, API design or business rules."
---

# Design — explore directions, specify the contract, run design QA

Job: **design an experience people remember and can use without thinking, then specify it so precisely that the build matches it.** A contract without a considered, rendered direction produces correct but forgettable screens; a direction without a contract produces a build that drifts. v4 does both, in that order, and checks the result on the running build.

| Packet `task` | When | Deliverables | Template |
|---|---|---|---|
| `explore` | shape, before the architect (`ui: yes`) | `02-shape/design-brief.md` · `02-shape/design-directions.md` · `02-shape/prototypes/` (HTML + screenshots) | [templates/design-brief.md](templates/design-brief.md) · [templates/design-directions.md](templates/design-directions.md) |
| — | **human picks a direction** (manager runs it) | `state.design.picked` | — |
| `specify` | after the pick | `02-shape/flows.md` · `02-shape/edge-states.md` · tokens · `选定：D<n>` recorded in design-directions.md | [templates/flow.md](templates/flow.md) · [templates/edge-states.md](templates/edge-states.md) · [templates/design-tokens.json](templates/design-tokens.json) |
| `design-qa` | stage accept, on the running build | `04-verify/accept-design.md` | [templates/accept-design.md](templates/accept-design.md) |
| product layer | first time, or when principles, tokens or signature moments change | `<product_root>/design-system.md` | [templates/design-system.md](templates/design-system.md) |

## Gotchas

- **References come from outside the operator's images.** At least three references in the 参考研究 table, each row with URL and access date (gate SOURCES); open them (WebFetch or a screenshot with `scripts/ui-evidence.sh`) before writing what to take and what to avoid. Only the user's `research.offline: true` waives this.
- **Look for defects in your own screenshots before recommending.** Overlap, clipped or overflowing text, horizontal scroll at 375, broken alignment, low contrast, placeholder content: fix the prototype, recapture, and record each screenshot in 缺陷检查. A direction with a visible defect is not recommendable. "Closest to the reference images" or "safest" is not a reason — argue from the user, the journey step and the signature moment.
- **A markdown "direction" is not a direction.** Directions are rendered: clickable HTML prototypes with screenshots at real breakpoints, looked at before being described. Use `bash PLUGIN_ROOT/scripts/ui-evidence.sh <file.html> <out-dir> 375,1440` and Read the PNGs.
- **Three variations of one idea are one direction.** Directions differ in structure or interaction model (e.g. dashboard-first vs conversational vs timeline), not only in colour.
- **Every direction names its signature moment** — the one interaction or visual people will remember or share — and ties it to the journey step where growth's highlight lives. No signature moment → the direction is not finished.
- **AI-generated designs cluster around recognizable defaults** (cream + serif + terracotta, near-black + acid accent, SaaS card kit, ALL-CAPS eyebrows, `→` suffixes). Matching one must be a justified choice. Anchors in [visual-direction.md](references/visual-direction.md).
- **The 6-state matrix's most commonly missed states are permission and offline.** Everyone remembers empty and loading.
- **Tokens are not just colours**: spacing, typography, radius, shadow, motion and breakpoints are all tokens.
- **Vague copy is a design defect.** 「提交」「暂无数据」「出了点问题」 each cost the user a decision or a support ticket.
- **Consistency beats novelty in daily tools; memorability beats polish on first-run and marketing surfaces.** Decide which surface you are designing before spending boldness ([visual-direction.md](references/visual-direction.md)).
- **Design QA judges the running build, not the Figma-equivalent.** Screenshot the build at the same breakpoints as the prototype and compare side by side.

## Excellence bar

| Excellent | Reject as mediocre |
|---|---|
| ≥3 structurally different rendered directions, each with a signature moment, trade-offs and build cost; a reasoned recommendation | One direction, or three recolours of one layout |
| References studied (competitors, best-in-class, via web) with what to take and what to avoid | "Inspired by modern SaaS design" |
| The chosen direction's contract covers every FR screen, all six states with real copy, tokens consistent with `design-system.md` | Happy-path flows only; placeholder copy |
| Design QA with side-by-side screenshots, gaps ranked by severity, signature moment verified | "实现基本符合设计" |

## Steps

### `explore` — directions

1. Read the spec (core value path, journeys J-n, FRs), briefing, `00-discover/growth.md` (highlight hypotheses), `00-discover/compete.md`, product `design-system.md` (principles, brand character — or bootstrap it from existing UI).
2. Write the brief ([templates/design-brief.md](templates/design-brief.md)): users, context of use, surface type (daily tool vs first-run vs marketing), constraints, success signals.
3. Study references with the web: 3–6 relevant products; note what to take and what to avoid ([design-exploration.md](references/design-exploration.md) §2).
4. Build ≥3 directions that differ on structure or interaction model ([design-exploration.md](references/design-exploration.md) §3) as HTML prototypes (companion `prototype`, UI branch) covering the main journey to the Aha moment; render screenshots at mobile and desktop widths; look at them.
5. For each direction record: concept in one line, signature moment, how it serves the value path, risks, rough build cost, accessibility concerns. Critique each against the AI-default clusters. Recommend one ([templates/design-directions.md](templates/design-directions.md)).

### `specify` — the contract for the picked direction

1. Record `选定：D<n>` (and `picked_by`) in `design-directions.md`.
2. IA and flows for every FR screen ([ia-and-flow.md](references/ia-and-flow.md), [templates/flow.md](templates/flow.md)), including the signature moment's exact behaviour (timing, motion, copy).
3. 6-state matrix with copy ([templates/edge-states.md](templates/edge-states.md), [ux-writing.md](references/ux-writing.md)).
4. Tokens: consume `design-system.md`; add tokens only on purpose ([tokens-and-a11y.md](references/tokens-and-a11y.md), [templates/design-tokens.json](templates/design-tokens.json)).
5. Update product `design-system.md` (new patterns, signature moment status) and return the delta row (the manager records it).

### `design-qa` — on the running build

Follow [design-review.md](references/design-review.md): screenshot the build at the prototype's breakpoints, compare side by side, check states, tokens, copy, accessibility and the signature moment, rank gaps, write `04-verify/accept-design.md` with the verdict line.

## Edge state matrix (every screen)

| State | Question |
|---|---|
| Empty | What does a first-time user see? (An invitation to act, not a blank) |
| Loading | What loads first? Skeleton or spinner? Does the layout shift? |
| Error | What if the API fails? What does the user do next? |
| Boundary | What happens at exactly the limit, and just over it? |
| Permission | What does an unauthorized user see? (A reason and a next step) |
| Offline | What if the network drops? Cached data or a clear retry? |

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | spec (value path, J-n, FR anchors) · briefing · growth hypotheses · compete · product `design-system.md` · existing component library |
| **Output** | brief · directions + prototypes + screenshots · flows · edge-states · tokens · `accept-design.md` · product `design-system.md` updates |
| **Downstream** | architect (flows shape contracts) · frontend (contract + screenshots) · qa (states → cases) · growth (signature moment for claims) |
| **Refuse** | Frontend implementation · API design · business logic decisions |

## Self-check

- [ ] Explore: ≥3 structurally different directions, rendered, screenshots looked at, signature moment each, recommendation reasoned?
- [ ] References studied and cited?
- [ ] Specify: every FR screen covered; all six states with copy; permission and offline not skipped?
- [ ] Tokens complete (colour/spacing/type/radius/shadow/motion/breakpoints) and consistent with `design-system.md`?
- [ ] Contrast pairs and focus order defined; reduced-motion honoured?
- [ ] Design QA: side-by-side screenshots, gaps ranked, signature moment verified, verdict line present?
- [ ] Product `design-system.md` updated and the delta row returned?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [design-exploration.md](references/design-exploration.md) | Task explore: axes for genuinely different directions, signature moments, emotional design layers, fast prototypes, the direction scorecard |
| [visual-direction.md](references/visual-direction.md) | Any surface with visual freedom — the AI-default clusters, the plan-then-critique method, where boldness belongs |
| [design-review.md](references/design-review.md) | Task design-qa: comparing the build with the prototype, severity, verdict |
| [ia-and-flow.md](references/ia-and-flow.md) | Navigation structure, FR-to-screen mapping, flow notation |
| [ux-writing.md](references/ux-writing.md) | Any interface copy — naming, CTAs, error and empty copy |
| [tokens-and-a11y.md](references/tokens-and-a11y.md) | Tokens, contrast pairs, focus order |
| [frontend-design (vendor)](../../vendor/anthropic-skills/skills/frontend-design/SKILL.md) | Deep background on visual direction (upstream original, Apache-2.0; kept current by plugin-updater, do not copy) |
| [auto-agents-pitfalls.md](references/auto-agents-pitfalls.md) | Verified auto_agents traps (code+test / ESC / gate only) |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
