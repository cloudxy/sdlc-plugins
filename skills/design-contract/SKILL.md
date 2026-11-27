---
name: "design-contract"
description: "Use this skill when the spawn packet names designer or $design-contract. Do NOT load in /sdlc or for frontend code."
when_to_use: "Spawn packet names designer (task explore / specify / design-qa), or $design-contract. Do NOT use from parent /sdlc. Do NOT use for frontend implementation, API design or business rules."
---

# Design — explore directions, specify the contract, run design QA

Job: **design an experience people remember and can use without thinking, then specify it so precisely that the build matches it.** A contract without a considered, rendered direction produces correct but forgettable screens; a direction without a contract produces a build that drifts. v4 does both, in that order, and checks the result on the running build.

| Packet `task` | When | Deliverables | Template |
|---|---|---|---|
| `explore` | shape, before the architect (`ui: yes`) | `02-shape/design-brief.md` · `02-shape/design-directions.md` · `02-shape/prototypes/D<n>/` (HTML + screenshots) | [templates/design-brief.md](templates/design-brief.md) · [templates/design-directions.md](templates/design-directions.md) |
| — | **human picks a direction** (manager runs it) | `state.design.picked` | — |
| `specify` | after the pick | `02-shape/flows.md` · `02-shape/edge-states.md` · tokens · `02-shape/prototypes/final/` (handoff prototype + screenshots) · `选定：D<n>` recorded in design-directions.md | [templates/flow.md](templates/flow.md) · [templates/edge-states.md](templates/edge-states.md) · [templates/design-tokens.json](templates/design-tokens.json) |
| `design-qa` | stage accept, on the running build | `04-verify/accept-design.md` | [templates/accept-design.md](templates/accept-design.md) |
| product layer | first time, or when principles, tokens or signature moments change | `<product_root>/design-system.md` | [templates/design-system.md](templates/design-system.md) |

## Local refinement

A named flow/page can be refined against its accepted requirement and design baseline. Record feedback, affected states and a concrete completion criterion; reuse settled components/directions. A changed business outcome goes to PM, a feasibility conflict to architecture. Ordinary preference iteration does not count as failed technical rework. Discovery prototypes may help clarify requirements; final handoff prototypes still need accepted behavior. Return the input/output versions and affected consumers, including prior design acceptance needing revalidation.

For an already accepted local direction, apply the steps below to the affected states and deliverables; do not invent a new D<n> selection or approval cycle. A short change contract can hand off an unambiguous refinement. Unresolved structure or interaction needs an appropriate prototype; claims about rendered layout or the running build still require actual visual evidence. Use [interaction-preserving-refinement.md](references/interaction-preserving-refinement.md) for existing menus, libraries, settings and tools with asynchronous results or saved history. In those tools, specify which input and run the visible result belongs to, and what refresh, failure and explicit history selection restore. When sibling views on one page share a category row and a tool row, that reference also fixes those two row heights and the vertical origin of the first content.

## Choose the scope before exploring

Record mode `reuse`, `local-exploration` or `new-direction`, why it fits, the approved baseline/version and unresolved decisions. Reuse existing components/tokens and direction when valid; no new visual competition or external research is required for a settled local change. New consequential choices need credible alternatives and an authorized selection, not a fixed number. Cite existing user/delegated authority instead of asking again. Early architecture feasibility may precede final design.

## UX & Design Engineering Canon (non-negotiable laws)

Apply these laws across `explore`, `specify` and `design-qa` (details in [ia-and-flow.md](references/ia-and-flow.md), [visual-direction.md](references/visual-direction.md), [tokens-and-a11y.md](references/tokens-and-a11y.md)):

- **Tesler's Law (Conservation of Complexity):** absorb irreducible complexity in smart defaults, system inference and progressive disclosure instead of exposing raw configuration knobs to users.
- **`UI = f(Authoritative State)` Isomorphism:** define optimistic UI rollback feedback on server rejection, preserve form/modal drafts on 4xx/5xx or back-navigation, and specify **forward migration for hidden/deprecated cached steps or localStorage drafts** so stale hidden client parameters never silently execute.
- **Jakob's Law & Novelty Budget:** preserve familiar conventions in daily high-frequency workbenches; spend visual/interaction boldness on first-run Aha, signature moments and marketing surfaces.
- **Hick's Law & Miller's Law:** one unmistakable primary CTA per screen/container with progressive disclosure for secondary controls; chunk navigation, filters and scannable groups into `5–7` meaningful items.
- **Fitts's Law:** interactive touch/click targets `≥ 44×44px` (including padding), primary actions near focus/selection locus, and **physical + visual separation of destructive actions** from frequent confirm/save actions (with confirmation or undo).
- **Gestalt Over Card-Border Soup:** group related elements via **proximity, alignment and whitespace** rather than nesting cards inside bordered cards (`SaaS 卡片套娃`).
- **Doherty Threshold:** `<100ms` direct-manipulation feedback; `<400ms` unbroken task flow; `>200ms` stable-geometry skeleton or stale-while-revalidate (no `<200ms` flash, zero layout shift); `>10s` non-blocking async progress + cancel + server-recoverable state.
- **WCAG AA:** `≥4.5:1` body text, `≥3:1` large text / UI borders / focus ring, non-colour second channel (icon/copy), explicit keyboard Tab/Escape focus order, `aria-label` copy on icon buttons, and `prefers-reduced-motion`.

## Gotchas

- **References come from outside the operator's images.** Use relevant project/user references first; research externally for actual unknowns. External claims need accessed sources/dates and limitations; no source-count quota or compulsory web research for reuse.
- **Look for defects in your own screenshots before recommending.** Overlap, clipped or overflowing text, horizontal scroll at 375, broken alignment, low contrast, placeholder content: fix the prototype, recapture, and record each screenshot in 缺陷检查. A direction with a visible defect is not recommendable. "Closest to the reference images" or "safest" is not a reason — argue from the user, the journey step and the signature moment.
- **A markdown "direction" is not a direction.** Directions are rendered: clickable HTML prototypes with screenshots at real breakpoints, looked at before being described. Use `bash PLUGIN_ROOT/scripts/ui-evidence.sh <file.html> <out-dir> 375,1440` and Read the PNGs.
- **Three variations of one idea are one direction.** Directions differ in structure or interaction model (e.g. dashboard-first vs conversational vs timeline), not only in colour.
- **Where distinctiveness is an agreed goal, name its signature moment** — the one interaction or visual people will remember or share — and ties it to the journey step where growth's highlight lives. Routine workflows may instead prioritize task clarity and consistency; record that choice.
- **AI-generated designs cluster around recognizable defaults** (cream + serif + terracotta, near-black + acid accent, SaaS card kit, ALL-CAPS eyebrows, `→` suffixes). Matching one must be a justified choice. Anchors in [visual-direction.md](references/visual-direction.md).
- **The 6-state matrix's most commonly missed states are permission and offline.** Everyone remembers empty and loading.
- **Unknown is not denied, failure is not empty.** Permissions still loading, a failed load and a truly empty list each need their own state and copy; showing a failure or an unloaded permission set as 「暂无」 or hidden navigation tells users the product has nothing.
- **An in-flight catalog is loading, not empty.** Before a prepared result arrives, the count stays in its loading treatment and the list shows the loading state. Empty copy is only for a result that has arrived and is empty. A fixed page size is a boundary: adding a few records changes the total, not how many cards the first screen or each next page draws. Switching among a small set of categories shows an already prepared default first page immediately, and refreshing that page does not flash the empty state.
- **Tokens are not just colours**: spacing, typography, radius, shadow, motion and breakpoints are all tokens.
- **Vague copy is a design defect.** 「提交」「暂无数据」「出了点问题」 each cost the user a decision or a support ticket.
- **Consistency beats novelty in daily tools; memorability beats polish on first-run and marketing surfaces.** Decide which surface you are designing before spending boldness ([visual-direction.md](references/visual-direction.md)).
- **Design QA judges the running build, not the Figma-equivalent.** Screenshot the build at the same breakpoints as the prototype and compare side by side.

## Excellence bar

| Excellent | Reject as mediocre |
|---|---|
| Appropriate reuse or credible rendered alternatives for an unresolved choice, with trade-offs and recommendation | Unjustified redesign, or nominal variants that do not address the unresolved question |
| Exploring an unresolved choice: references studied (competitors, best-in-class, via web) with what to take and what to avoid; a settled `reuse` cites the approved baseline instead | "Inspired by modern SaaS design" |
| The chosen direction's contract covers every FR screen, all six states with real copy, tokens consistent with `design-system.md` | Happy-path flows only; placeholder copy |
| Design QA with side-by-side screenshots, gaps ranked by severity, signature moment verified | "实现基本符合设计" |

## Steps

### `explore` — directions

1. Read the spec (core value path, journeys J-n, FRs), briefing, `00-discover/growth.md` (highlight hypotheses), `00-discover/compete.md`, product `design-system.md` (principles, brand character — or bootstrap it from existing UI).
2. Write the brief ([templates/design-brief.md](templates/design-brief.md)): users, context of use, surface type (daily tool vs first-run vs marketing), constraints, success signals.
3. Study references with the web: relevant sources for unresolved questions; note what to take and what to avoid ([design-exploration.md](references/design-exploration.md) §2).
4. Reuse the approved direction, or build credible alternatives differing on structure or interaction model ([design-exploration.md](references/design-exploration.md) §3) as HTML prototypes to the standard in [direction-prototypes.md](references/direction-prototypes.md) (not the throwaway `prototype` skill) covering the main journey to the Aha moment; render screenshots at mobile and desktop widths; look at them.
5. For each direction record: concept in one line, signature moment, how it serves the value path, risks, rough build cost, accessibility concerns. Critique each against the AI-default clusters. Recommend one ([templates/design-directions.md](templates/design-directions.md)).

### `specify` — the UX engineering behavior contract for the picked direction

1. Record `选定：D<n>` (and `picked_by`) in `design-directions.md`.
2. **IA, flows & 4 hard specification fields** for every FR screen ([ia-and-flow.md](references/ia-and-flow.md), [templates/flow.md](templates/flow.md)), including the signature moment's timing, motion and copy:
   - ① **Component inventory** citing canonical `product_root/design-system.md` source IDs (zero orphan ad-hoc components);
   - ② **Zero-`TBD` microcopy** — every label, CTA, tooltip, toast, empty and error string finalized ([ux-writing.md](references/ux-writing.md); never `TBD` left to `frontend`);
   - ③ **Explicit responsive layout rules per breakpoint (`375 / 768 / 1440`)** — column collapse, drawer/modal adaptation, overflow and `≥44×44px` targets;
   - ④ **Design-time accessibility** — `role`, `aria-label`, keyboard keys, contrast pairs and Tab focus order ([tokens-and-a11y.md](references/tokens-and-a11y.md)).
3. **Dual-axis state fusion:** pair the **Interactive Component 7-State Checklist** (`default, hover/focus, disabled, loading, empty, error, success`) in `flows.md` with the **Screen Data/Env 6-State Matrix** (`loading, empty, error, permission, boundary, offline`) in `edge-states.md` ([templates/edge-states.md](templates/edge-states.md)).
4. Tokens: consume `design-system.md`; add tokens only on purpose ([templates/design-tokens.json](templates/design-tokens.json)).
5. Final prototype for handoff: every FR screen and edge state, tokens only, canonical component IDs, screenshots inspected ([direction-prototypes.md](references/direction-prototypes.md) § Final prototype).
6. Update product `design-system.md` with accepted patterns/token links (proposed vs implemented distinct) and return the delta row.

**UX Exit Gate:** `frontend` implements components with **zero guessing**; `qa` derives empty/error/loading/boundary cases directly from the spec.

### `design-qa` — on the running build

Follow [design-review.md](references/design-review.md): screenshot the build at the prototype's breakpoints, compare side by side, check states, tokens, copy, accessibility and the signature moment, rank gaps, write `04-verify/accept-design.md` with the verdict line.

## Dual-axis state specification (Screen 6-State × Component 7-State)

Fuse screen-level data/environment states (`edge-states.md`) with interactive control states (`flows.md`):
- **Interactive Component 7-State Checklist (`flows.md`):** `default` · `hover/focus` · `disabled` · `loading` · `empty` · `error` · `success` (mark inapplicable control states `➖` with a 1-line reason).
- **Screen Data/Env 6-State Matrix (`edge-states.md`):**

| State | Question |
|---|---|
| Loading | What loads first? Skeleton or spinner (`>200ms`)? Does the layout shift? |
| Empty | First-time empty vs filter-empty? (An invitation to act, never 「暂无数据」) |
| Error | What per contract `code` + fallback? What does the user do next without losing input? |
| Permission | Hide vs disable + reason? What does an unauthorized deep-link user see? |
| Boundary | What happens at 0, 1, exact limit, over-limit, long text and extreme numbers? |
| Offline | What if the network drops? Cached data, reconnect banner or explicit `➖` reason? |

## Handoff contract

| Direction | Content |
|---|---|
| **Input** | spec (value path, J-n, FR anchors) · briefing · growth hypotheses · compete · product `design-system.md` · existing component library |
| **Output** | brief · directions + prototypes + screenshots · flows · edge-states · tokens · `accept-design.md` · product `design-system.md` updates |
| **Downstream** | architect (flows shape contracts) · frontend (final prototype code/version, component IDs, canonical tokens, flows/states; screenshots as reference) · qa (states → cases) · growth (signature moment for claims) |
| **Refuse** | Frontend implementation · API design · business logic decisions |

## Self-check

- [ ] Explore: scope mode justified, reuse/selection authority cited, applicable directions rendered and inspected, recommendation grounded?
- [ ] `new-direction` or an exploration with open questions: references studied and cited? (`reuse` cites the approved baseline and version instead)
- [ ] Specify: every FR screen covered; Component 7-State Checklist (`flows.md`) fused with Screen 6-State Matrix (`edge-states.md`); permission/offline explicitly assessed?
- [ ] All 4 hard fields complete: canonical `design-system.md` component IDs (zero ad-hoc orphans), **zero-`TBD` microcopy**, `375 / 768 / 1440` breakpoint layout rules, and design-time a11y (`role`, `aria-label`, keyboard keys, contrast pairs, Tab focus order)?
- [ ] UX Exit Gate met: `frontend` builds with zero guessing and `qa` derives empty/error/loading/boundary cases directly from the spec?
- [ ] Tokens complete (colour/spacing/type/radius/shadow/motion/breakpoints) and consistent with `design-system.md`; `prefers-reduced-motion` honoured?
- [ ] Design QA: side-by-side screenshots, gaps ranked, signature moment verified, verdict line present?
- [ ] Product `design-system.md` updated and the delta row returned?
- [ ] For asynchronous tools: current draft, submitted inputs, current result and saved history have explicit lifetimes; refresh and partial-save failure follow the authorized behavior rather than an implicit latest-history fallback?

## Deep references — when to read them

| Reference | Read when… |
|---|---|
| [direction-prototypes.md](references/direction-prototypes.md) | Tasks explore and specify: direction prototypes vs the final handoff prototype, paths, quality bar, evidence types |
| [design-exploration.md](references/design-exploration.md) | Task explore: axes for genuinely different directions, signature moments, emotional design layers, fast prototypes, the direction scorecard |
| [visual-direction.md](references/visual-direction.md) | Any surface with visual freedom — the AI-default clusters, the plan-then-critique method, where boldness belongs |
| [design-review.md](references/design-review.md) | Task design-qa: comparing the build with the prototype, severity, verdict |
| [ia-and-flow.md](references/ia-and-flow.md) | Navigation, collection semantics, compact cards, FR-to-screen mapping and flow notation |
| [interaction-preserving-refinement.md](references/interaction-preserving-refinement.md) | Existing menus, libraries and settings; shared controls across page themes; in-place sibling views that share a category row and a tool row; retained actions, focus and narrow-screen states |
| [ux-writing.md](references/ux-writing.md) | Any interface copy — naming, CTAs, error and empty copy |
| [tokens-and-a11y.md](references/tokens-and-a11y.md) | Tokens, contrast pairs, focus order |
| [generated-imagery.md](references/generated-imagery.md) | The packet lists `imagery` — when a generated image is worth it, where its style anchors come from, how it lands in an artifact (a reference image is never the direction) |
| [frontend-design (vendor)](../../vendor/anthropic-skills/skills/frontend-design/SKILL.md) | Deep background on visual direction (upstream original, Apache-2.0; kept current by plugin-updater, do not copy) |

## Role-specific review

For the assigned role, apply [references/role-quality.md](references/role-quality.md) alongside this procedure’s self-check. Reviewers use the same criteria.
